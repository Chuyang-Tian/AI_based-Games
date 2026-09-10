from pathlib import Path
import argparse
import markdown


CSS = """
body { font-family: "Microsoft YaHei", Arial, sans-serif; color: #222; margin: 0; background: #f5f7fb; }
main { max-width: 960px; margin: 0 auto; background: #fff; padding: 40px 56px; box-sizing: border-box; }
h1, h2, h3 { color: #111827; }
h1 { font-size: 30px; border-bottom: 3px solid #2563eb; padding-bottom: 12px; }
h2 { font-size: 22px; margin-top: 36px; border-left: 5px solid #2563eb; padding-left: 10px; }
h3 { font-size: 18px; margin-top: 24px; }
p, li { font-size: 14px; line-height: 1.8; }
ul, ol { padding-left: 24px; }
code { background: #f3f4f6; padding: 2px 6px; border-radius: 4px; font-family: Consolas, monospace; }
pre code { display: block; padding: 14px; overflow-x: auto; }
table { width: 100%; border-collapse: collapse; margin: 18px 0; font-size: 13px; }
th, td { border: 1px solid #d1d5db; padding: 8px 10px; vertical-align: top; }
th { background: #eff6ff; }
img { display: block; max-width: 100%; margin: 14px auto 26px; border: 1px solid #d1d5db; box-shadow: 0 4px 14px rgba(0,0,0,0.08); }
blockquote { margin: 16px 0; padding: 10px 14px; background: #f9fafb; border-left: 4px solid #93c5fd; }
hr { border: none; border-top: 1px solid #e5e7eb; margin: 30px 0; }
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert report markdown to HTML.")
    parser.add_argument("markdown_path")
    parser.add_argument("html_path")
    args = parser.parse_args()

    md_path = Path(args.markdown_path)
    html_path = Path(args.html_path)

    text = md_path.read_text(encoding="utf-8")
    body = markdown.markdown(
        text,
        extensions=["extra", "tables", "fenced_code", "sane_lists"],
    )
    html = (
        "<!doctype html><html lang=\"zh-CN\"><head>"
        "<meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        "<title>OJ 调试平台实验报告</title>"
        f"<style>{CSS}</style>"
        "</head><body><main>"
        f"{body}"
        "</main></body></html>"
    )
    html_path.write_text(html, encoding="utf-8")
    print(html_path)


if __name__ == "__main__":
    main()
