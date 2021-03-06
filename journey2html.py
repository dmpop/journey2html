#!/usr/bin/env python3
"""
Generating static HTML files from Journey backups

The HTML file "index.html" is stored in the directory named
by the original ZIP backup.

For example, ZIP file is "journey-foo.zip" the HTML file
is stored as "journey-foo/index.html".
"""

import argparse
import datetime
import json
import markdown
from pathlib import Path
import sys
import zipfile

import lxml
from lxml.html import builder as E, fromstring

__version__ = "0.1.0"
__date__ = "2017-11-09"
__author__ = "Thomas Schraitle (actual coder), Dmitri Popov (idle bystander)"

# The default input and output encoding for the resulting HTML file
ENCODING = 'UTF-8'

#
CSSFILE = "https://unpkg.com/sakura.css/css/sakura-dark.css"


def listjsonfiles(directory):
    """Yields a list of JSON files

    :param directory: directory name
    :type directory: str
    :return: yields all JSON files in the given directory
    """
    d = Path(directory)
    yield from d.glob("*.json")


def convert_date(datestr, timezone=None):
    """Convert date and time from POSIX to ISO format

    :param datestr: integer of POSIX time; the last three digits are
                    microseconds
                    for example: "1509022007088" => 1509022007.088
    :type datestr: int
    :return: returns the ISO format ('2017-10-26T14:46:47' in our
             example)
    """
    return datetime.datetime.fromtimestamp(int(datestr/1000)).strftime('%B %d, %Y %H:%M')


def load_jsonfile(jfile, encoding=ENCODING):
    """Load a single JSON file

    :param jfile: filename of a JSON file
    :type jfile: :class:`pathlib.PosixPath`
    :return: returns the relevant content of the JSON file
    """
    content = {}
    try:
        with jfile.open(encoding=encoding) as fh:
            src = json.load(fh)
            for key in ("text", "photos", "address", "date_journal"):
                content[key] = src.get(key)
        # Convert the date:
        content["date_journal"] = convert_date(content["date_journal"])
    except ValueError as error:
        print("ERROR (in %r): %s" % (str(jfile), error), file=sys.stderr)
        sys.exit(10)
    return content


def gen_html(encoding=ENCODING):
    """Create the HTML structure

    :return: Return the body structure from lxml.html
    """
    body = E.BODY()
    html = E.HTML(E.HEAD(
            E.LINK(rel="stylesheet", href=CSSFILE, type="text/css"),
            E.META(charset=encoding),
        ),
        body)
    return body


def expand_ziparchive(ziparchive, zipdir):
    """Expand the ZIP archive into a directory

    :param ziparchive: Path to ZIP file
    :type ziparchive: Path | str
    :param zipdir: directory to extract all ZIP content
    :type zipdir: Path | str
    """
    with zipfile.ZipFile(str(ziparchive)) as zz:
        zz.extractall(str(zipdir))


def process_jsonfiles(zipdir):
    """Process all JSON files in the resulting directory

    :param zipdir: zipdir name
    :type zipdir: Path | str
    """
    body = gen_html()

    for jfile in listjsonfiles(str(zipdir)):
        content = load_jsonfile(jfile)
        # Create title
        div = E.DIV(E.H1(content.get("date_journal")))

        # Create date:
        div.append(E.H5(content.get("address")))

        # Create photos:
        divimg = E.DIV()
        for image in content.get('photos'):
            img = E.IMG(src=image, width="600", )
            divimg.append(img)
        div.append(divimg)

        # Create text:
        text = content["text"] = markdown.markdown(content["text"])
        texthtml = fromstring(text)
        div.append(E.P(texthtml))

        body.append(div)
    return body


def output_html(tree, htmlfile, *, encoding=ENCODING, pretty_print=True):
    """Output the HTML tree to a file

    :param tree: the HTML tree
    :param htmlfile: the name of the resulting HTML file
    :param encoding: the encoding
    :param pretty_print: should the output be pretty printed?
    """
    tree.write(str(htmlfile), encoding=encoding, pretty_print=pretty_print)


def parsecli():
    """Parse the command-line arguments

    :return: returns the :class:`argparse.Namespace` class
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', action='version',
                        version='%(prog)s {}'.format(__version__))
    # Add options here...
    parser.add_argument('zipfile',
                        # default=".",
                        help="Path to ZIP file (including filename)",
                        )
    args = parser.parse_args()
    zf = Path(args.zipfile)
    args.zipdir = Path(Path(zf).stem)
    if not zf.exists():
        parser.error("ZIP file %s does not exist." % zf)

    if args.zipdir.exists():
        parser.error("Directory %s already exists." % args.zipdir)

    args.htmlfile = args.zipdir.joinpath("index.html")
    return args


def process(args):
    """Process everything and catch any errors

    :param args: result from argparse
    """
    try:
        expand_ziparchive(args.zipfile, args.zipdir)
        html = process_jsonfiles(args.zipdir).getroottree()
        output_html(html, str(args.htmlfile))
    except (FileNotFoundError, ) as error:
        print("ERROR: %s" % error, file=sys.stderr)
        sys.exit(20)


if __name__ == "__main__":
    args = parsecli()
    process(args)
