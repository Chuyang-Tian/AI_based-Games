from pathlib import Path
import argparse
import requests


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch anti-AI review HTML and save a standalone preview file.")
    parser.add_argument("--base", default="http://127.0.0.1:5001")
    parser.add_argument("--submission-id", type=int, required=True)
    parser.add_argument("--username", default="admin")
    parser.add_argument("--password", default="admintestpassword")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    session = requests.Session()
    login = session.post(
        f"{args.base}/api/auth/login",
        json={"username": args.username, "password": args.password},
        timeout=10,
    )
    login.raise_for_status()

    resp = session.get(
        f"{args.base}/api/ai/submissions/{args.submission_id}/review",
        timeout=10,
    )
    resp.raise_for_status()
    payload = resp.json().get("data") or {}
    html = payload.get("report_html") or ""
    wrapper = (
        "<!doctype html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\">"
        "<title>反AI审查截图素材</title></head>"
        "<body style=\"margin:24px;background:#ffffff;\">"
        f"{html}"
        "</body></html>"
    )
    out = Path(args.output)
    out.write_text(wrapper, encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
