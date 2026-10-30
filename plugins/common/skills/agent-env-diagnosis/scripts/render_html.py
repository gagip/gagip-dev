#!/usr/bin/env python3
"""template.html 에 report_data.json 을 넣어 진단 HTML 한 장을 만든다."""

import argparse
import os


def render(data_text, template_text):
    safe = data_text.replace("</", "<\\/").replace("<!--", "<\\u0021--")
    return template_text.replace("__DATA__", safe)


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--out-dir", required=True)
    p.add_argument("--html", help="출력 경로 (기본: <out-dir>/diagnosis.html)")
    args = p.parse_args(argv)
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "template.html"), encoding="utf-8") as fh:
        tpl = fh.read()
    with open(os.path.join(args.out_dir, "report_data.json"), encoding="utf-8") as fh:
        data = fh.read()
    out = args.html or os.path.join(args.out_dir, "diagnosis.html")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(render(data, tpl))
    print(out)


if __name__ == "__main__":
    main()
