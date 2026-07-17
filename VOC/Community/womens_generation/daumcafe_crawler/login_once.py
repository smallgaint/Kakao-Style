from pathlib import Path

from playwright.sync_api import sync_playwright


STORAGE = Path("auth/daum_storage_state.json")


def main():

    STORAGE.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=False
        )

        context = browser.new_context()

        page = context.new_page()

        page.goto(
            "https://cafe.daum.net/subdued20club",
            wait_until="networkidle"
        )

        print("=" * 80)
        print("브라우저에서 카카오 로그인을 완료하세요.")
        print("여성시대 카페 메인 화면까지 들어간 뒤 Enter를 누르세요.")
        print("=" * 80)

        input()

        context.storage_state(
            path=str(STORAGE)
        )

        print()
        print("로그인 세션 저장 완료!")
        print(STORAGE.resolve())

        browser.close()


if __name__ == "__main__":
    main()