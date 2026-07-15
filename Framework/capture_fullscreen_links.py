from pathlib import Path

try:
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
    from playwright.sync_api import sync_playwright
except ModuleNotFoundError as exc:
    raise SystemExit(
        "Playwright is not installed.\n"
        "Install it with these commands:\n"
        "  pip install playwright\n"
        "  python -m playwright install chromium"
    ) from exc


# 1) Put target URLs here.
LINKS = [
    "https://cr.shopping.naver.com/adcr?x=qxqqf9qSHVutDTxaeB8m9v%2F%2F%2Fw%3D%3DsKRKR90dbcK4iAdu1caxinYpACabOhFCsl714YtGBGiO6WcarJJTRVP8OnWoYySDJ0qAVHbRLX%2BsbxSCDhMJEREDvU%2Ba8%2F7b1XxWOpMPnRA7DpmNu2Rs3tEPrV0ZTODsb7JQtrMqSgEftbsAH7BzOjoMAlJ0J%2FkIR1fs3ubYsnkc7SFve%2F1dFJAD1ki2mh2Iwb%2Blyd%2FJC0U9tt5rrM5y6BzAP24UqIOxrOfyV5D1VfDMsZ0r88db9CMAHKpwjpH1jG%2F%2BtWgm8Lga%2BrsjZa2uru0Dczqr631%2FWo5FKHpdfFAQ9GhWayCLZXHkGbc%2FMNwXCngxBS8TsLQ1iUsnB2AVyn%2F7zUeFQVCp17ynnKm7SLp80O7Pt6JlWOQVbJVM%2BproTgGwmPNX%2Fe%2BXkuZ30duRQYj%2FN1gL%2FBgCKENDMCz1nm%2F30ohAeG78qm7kHHgTk2l9KignKRWPAsh6Pv%2F7THTWc%2Fya74mH1hTJLPQSph9rcpcR47zjGWLvYLg0G1NkPYnRLsIRZl%2FLCIkPysDq9ftG1HLI1SrqPmOVarEr6y2lzPvsW%2FKvUzdQGCTLR36hZGklRb10plbDqqIb1x5EWzkUvHBdOvDt5RwfimiMsFGmT870j5jI3d645RjpQyah0SlECkVDOmOxobawsGSqR%2FKqAVWkeX%2Fou5F2PMYDnosvzxWhLet8q47qPTMPOdPcTfsVfv1eeY8P%2FyYXyfNIJg0MVufzk2vzW4ojdO1zTKg18Bs%2BdoqEqCS64Mz66RjYk8iEc05%2FiL3MWsFcTbnjz%2FZLXrSa9rRNhL7VgZ%2B7C7wjeG%2BO0c6220JWdp2pCwTIafPPSch0BqmbFKlVrSrKMdCqUnQau4fTwOUqyF63FjwpQRls%3D&nvMid=53392330334&catId=50000807",
    "https://cr.shopping.naver.com/adcr?x=hEY5OQAzNvMOrANjaxNCyv%2F%2F%2Fw%3D%3DsygE%2Bd3AKo1i%2Fkq3XKEf64fohltcMufmb3bRd0U3nZUK6WcarJJTRVP8OnWoYySDJHuNZ4WiBNPPIrC6r2ktzFV%2FS2bI3oTa9Nxwus4SajK7DpmNu2Rs3tEPrV0ZTODsb7JQtrMqSgEftbsAH7BzOjoMAlJ0J%2FkIR1fs3ubYsnkc7SFve%2F1dFJAD1ki2mh2Iwb%2Blyd%2FJC0U9tt5rrM5y6BzAP24UqIOxrOfyV5D1VfDMsZ0r88db9CMAHKpwjpH1jaHn7kLyScuYS8Ysd%2F9Zq49QjPpsbQV7AdSI0XKjlA149GhWayCLZXHkGbc%2FMNwXCngxBS8TsLQ1iUsnB2AVyn%2F7zUeFQVCp17ynnKm7SLp80O7Pt6JlWOQVbJVM%2BproTgGwmPNX%2Fe%2BXkuZ30duRQYj%2FN1gL%2FBgCKENDMCz1nm%2F3mL%2FVlJT7AvYY92V4UnR52ignKRWPAsh6Pv%2F7THTWc%2Fya74mH1hTJLPQSph9rcpcR47zjGWLvYLg0G1NkPYnRLsIRZl%2FLCIkPysDq9ftG1HLI1SrqPmOVarEr6y2lzPvtDHUQhWy9ucEZsq1qnl8tCBtt3euksnvLJy83eO2h2APVrFGlMFUOhdnaVCWIqI38fIbhNUL0DGSPySjwlyyTu3LmIvJYjPPhqwqRJG1b2qgzdPfnB4%2FnZ8PsNI32JefrE0hZKXeNbLAkb8uiFb67c%2BBPUm5hw0wTtuKqqf%2FPERMQHjrwnd0O%2F2tc4ozsah5X7lJ6hNA8TsQAG8EFUkpA2OmgbxHRa3cupNPEcvq7F71%2FTbpVWdpmFbuGYwAghBpCCqA6%2BrrPkSkQjk3bFq%2FUy&nvMid=60504684660&catId=50000807",
    "https://cr.shopping.naver.com/adcr?x=HgvI%2FfogYP7b%2BDZHDbSt1f%2F%2F%2Fw%3D%3DsvpAKZg08COcTD7TCE0T34PE%2Bvg29lYDCVgqlD9dB9826WcarJJTRVP8OnWoYySDJaCyNO3OrZCV%2BnBl5WlSSZwN5IprmNGwXrvO%2FpuZTZ7XDpmNu2Rs3tEPrV0ZTODsb7JQtrMqSgEftbsAH7BzOjoMAlJ0J%2FkIR1fs3ubYsnkc7SFve%2F1dFJAD1ki2mh2Iwb%2Blyd%2FJC0U9tt5rrM5y6BzAP24UqIOxrOfyV5D1VfDMsZ0r88db9CMAHKpwjpH1j%2FZa%2FikgdoDE83iKjjWmlPy2z6HZl4XdSER3LxoLhb8OQzZ9hrlnUuMbkwqYWgHhGDiQdCgKhpD%2Fjt1BH2riF%2B89Y9NFysqWgdM9nytqF3URaLxM0FcEXwtUi%2FIYU6lKYueCfFDuywxl3T1PQ6PKMjF5qtMG%2FJ0PUtQjclakIAMiW2Q4u%2FJsLMNOpWchjU2UxzSTbcHPZgN3egubK2W4OhaOtpK48E85YH6OfOfhXYrHrOMrn5zP6RXDdSraAPJeAtUyLHdyYURiPAujaDFYpGd4uG3rW37iF1PhhFLSYOl5tJySmRzlqOw8PUM0Nc8zpYunD3W3i9ZDMcVFxWmYRIJT%2Fafo%2BCxP6q33WeF49ejylVNsNCOyxbEB4i5Y4qunx8NQtNwXw6c12Ds7v3E9yrOCu9Zyx0eCvc8H3U%2Bm71mCD4Nga3JEvCmAf6xVjK%2FNVRD3LlOQ5m12uuf8kDxjUXboSF04cLFgH4p%2FuyIKzRkJ%2Fl2JmeuE4WRO%2BFDNDA4HfLoIg4eUvJ%2Fu0XNDHjbs4HRQroICEhTsQYAIXt2lYjCTQ2mZnDuZGBoH%2B%2F46CoxW5xyAhEKTy%2B0Zvtn8oYxIR0Q%3D%3D&nvMid=50782599133&catId=50000807",
    "https://cr.shopping.naver.com/adcr?x=cHbG3Ds4OupA80VFarIdfP%2F%2F%2Fw%3D%3DsUSgef5zOWYlMEFUTv40Nq8D99ls9vsAv3r57A7aBlKK6WcarJJTRVP8OnWoYySDJ8UbGPsrW3lBkfQs9be%2ByM2y8DsUjvq2Sc8v0mcnCv0TDpmNu2Rs3tEPrV0ZTODsb7JQtrMqSgEftbsAH7BzOjoMAlJ0J%2FkIR1fs3ubYsnkc7SFve%2F1dFJAD1ki2mh2Iwb%2Blyd%2FJC0U9tt5rrM5y6BzAP24UqIOxrOfyV5D1VfDMsZ0r88db9CMAHKpwjpH1jw8AOK1bD9HJk158UApd2qg6mcQs8ASSUmRdzv16TxZyP%2Frsal5d73wKoXRRTGzbqayPHnSZLAQIRPzBxO3Dkwm14qlSzsWDSdy3w3n%2B6kL1G2WtRPY%2B0i9eY6j9i%2B1WMVV3pn6Znl%2B9MAtsEE%2BZ8ouacYsA2T1ONC2M4R1%2F3Eb%2BiuVf3Jh3BiS8Y1pCdE8Gq3hourSLEJgP3pmW9nsGomsjApG%2BhOjChOCsdN%2Fm4v72AXwThr673CyhkvrpUJmG9ky4OYKbGOLpIqCT93IZ3d2WJ4bmugam1O38ox4bfnVwxClhCc57d9mU32QpY88SvuVL%2FKLeZPRL5H8A3uhkx8iZ2GDXJR3qdYjWAiOgKf5Wr7piXfKnuW4AP4yYTKp4jws%2BRaiYFXWy2r1orLDNbGjC1DcYsDYzhVgiG9sQ3GEJJYNuMo1hSjliZ7JGQiw8UlBESZA4%2FdfgHgsu%2FhG2EBPP29OhjxOdxBxPuCZxs6pNGyUA3HeW8dEMtlmMt1l9i2cIwoE%2F9I11ggfRh5jDjjN0eriCZ6hzuWYHgat%2BF1h4aIbT4wPT2RVq4kndhIVrUzJ0eNP%2BjobzGQWGahcaypyLcQV6AzVWPMJY6Chlm8CWFbDf4gHI5rSMJU1BWcIOg&nvMid=59205514619&catId=50000807",
    "https://cr.shopping.naver.com/adcr?x=%2Ba6UarmfHUcNNCrSpCuH7P%2F%2F%2Fw%3D%3Ds%2BBAEiQ568Psq7XT5vC9hAYmVOTQ7VLymCx4IyNNIW2W6WcarJJTRVP8OnWoYySDJyEPh%2BpRK8S14btPaGSlo%2BPEmAKE7E2gQqAjIR8sdw4rDpmNu2Rs3tEPrV0ZTODsb7JQtrMqSgEftbsAH7BzOjoMAlJ0J%2FkIR1fs3ubYsnkc7SFve%2F1dFJAD1ki2mh2Iwb%2Blyd%2FJC0U9tt5rrM5y6BzAP24UqIOxrOfyV5D1VfDMsZ0r88db9CMAHKpwjpH1jWLfK3OOhtwVAT51q%2Fe16PZjnH23d2ZOJErHAK0Tf0WY9GhWayCLZXHkGbc%2FMNwXCngxBS8TsLQ1iUsnB2AVyn%2F7zUeFQVCp17ynnKm7SLp80O7Pt6JlWOQVbJVM%2BproTgGwmPNX%2Fe%2BXkuZ30duRQYj%2FN1gL%2FBgCKENDMCz1nm%2F37OoKYH9szPPzTzpNcgXEVignKRWPAsh6Pv%2F7THTWc%2Fya74mH1hTJLPQSph9rcpcR47zjGWLvYLg0G1NkPYnRLsIRZl%2FLCIkPysDq9ftG1HLI1SrqPmOVarEr6y2lzPvsgMkSHhI%2FCQf4ZadYKnd9p%2Fs9YYgJYZMc3tw5aGhF2ffVrFGlMFUOhdnaVCWIqI3%2BJNFAcMtb%2BDuPpsXc%2FkHLEdykM6cBGywG6Hz%2FmadnZZJce%2BkOWGcIhxeiP9ii9Y5o66Ws9eryVd2mmAa9xHxotJSRJdYOCX6pE3JNW1ACwaA48M37JzC2poe80bpe2jA7H0dpNklQT34a%2BeDyvrOw8a1jS8Ua1hwiaLnWMxworxnaEOcLu8XtgSNhqocrIy%2FTg8wzZphuwHW92meKcCEznb1NmOoRBMBsXNQGXzjfbC%2BFUQB%2FrDAzm2q1KHRsHkfE%3D&nvMid=59320198173&catId=50000807",
    "https://cr.shopping.naver.com/adcr?x=F5OZNJZHVF%2FfntiSyVO7Rf%2F%2F%2Fw%3D%3Dsp7buX1kSqaVK2tvjURBezVFxSsW%2FcJxRR1jtjXUlvMak4skwFu%2FUnk0YxYlolglCv1yrNp46dqDUYYOxGjsdSQB%2BzpWmWBGeGkADcO6MLZqAbCY81f975eS5nfR25FBiI1ODi9hUm3Sq0pLB9du%2BPiTNOfyt0x44eI3tLNXGqIdohZvmv%2B8xn01WENXfb6RC%2B3SlcFYXeJr0zFkl7%2BTtdkf2HVQZdpHBKYblTVkgOY55i2dHtUpL1VYMfVSa53ghrwHN4u5sBsyLY%2BeFwmL7f0iWE1I6NOPYcot6xc%2B3FVLC8qvS8ApUfHbA0wHvNiA3i5j2aQpAaVEYjaxMKp1jg8xr8nzK8G0AdS07kZQ0KzDO3aF9ryNnyUohuGK55zUCP2tfKoQ0NQPyiad34AQ6K9%2FdVvwtcOUlbNrGLU3RUnoib0yiWdw6wIfgVFHOcxJUvissG6ni7kQsVaujLG0hKdFH5nB2n%2BxnlJu4kz1z%2FNL9PMoVBks%2Bz1HNoDIF72zvTlbRcsxe8d7l3nI3%2FwYdkDriovvlx4BGA4GcoqVOlBORzDBm6hBB3a%2BdMndhYLREqj0sgheuwsQshuOU4Fju5FLaFD2pSB3PSu%2BxHJgL9phmd4ZkD8Ude21gcljvhPkuxEMu8IZXLcwo0JGnhA7KQp5PO%2BSKc4y7fZpNsEtjzc3xtv9AhX%2BYXtYVQbs%2FTpcotHx2yv2n50hhlf%2FKL5VAfRKUE40YXfTPEDep%2Fhaep5niEvcBl2Ek6QLvPXtVYSYkaAmVmWhC%2FLZECcxHQ8IhURA%2FQShgk8bw47r6omd%2FTOt%2B8O23Rc424A9e2a5CnhnpkQYR1c7SS1KyZ62hBlVVcqh6pyx6ePyd9CKkrLN3NtQdHI8FZtQVGFZJxOyBDKc%2B&nvMid=59986846653&catId=50000807"
    "https://cr.shopping.naver.com/adcr?x=ZkmkrC78udp%2FnDFQd426tf%2F%2F%2Fw%3D%3DsJZXWIVOZ7mWBUrtfO35ly2Vu3N4Odn4r0S%2FPa2g2tTDFa9lstMAPtCYCgArsthCjUhweFpdliS1MEe9yiJcY8GLaEsiwXIl59ucwGLkmjFND4P%2Bj2CVvS6QkrpszyaIo6sGkobrHOLjdQ9PfNparABJ4Vl90l4flK0DYjWpaflvKSYKk%2FbHmKYjfsK5wQICLT60wtQE6GhBSDK98oq8q3MKtU5HGyztr%2Fr4NOta52RN07Wce8SHFpmLj4fBZpgOq7aH0qtBLy7%2B2H3%2BljyTFuNFcZK90Lcw0DPNkVCrmPZL4JQO%2BVqY8ReLo111%2BdkTEFUDJ2BLpzzzsyWKLNS8gNaMOWtL97%2B0h%2FvTyTXJCEGD2%2BvOFWxe%2FHmTjxQBk9L1Lw6ZjbtkbN7RD61dGUzg7G1qsmhWtsS26cBgiQoajA6pKVi%2FrAJJ4y8u2Id3u6c9Svl5bcThNsPmuyaWoKxgjW5F5vdiy1pKokcNpmVNFhSwjKBN%2FVwjVGb9N6njK3fxcS2jynhrPwNnCpCBBRMOngnRHA4ZmIiWUJCdAMeh3rGVMA5K6d5yO3V8rMWhY%2BJhd2wENs5X8j72lGgLJkodUIwb8OWKICeFN%2B5TgTeZF1idYUD0FUEfPvBQ5aMXPm3VzH0dyCy%2BaUc2lWOn0a47wft5%2BaZt%2FIHl1hTmqqPOMAqMKCSPJMQ7QhkVU7ZLGe4%2FLp0XLTnwvjmNQ%2BhFhRi6od%2BRQBPDg3385nrIEh13mHHOxChwsQYZrTCyV4dzakWStKOqqWwnhORVpnKDMDOH4o7W7Ya8OvF09XdWAd1dQLeEDfkLIyuldBS3f8m8e6nLmzUhNzs2VE%2B%2Bisqs3JAEppg%3D%3D&nvMid=60783933360&catId=50000807",
    "https://cr.shopping.naver.com/adcr?x=7zzQk89MIIX1Pxoqd5gdd%2F%2F%2F%2Fw%3D%3Dst%2FVjjKokxa%2Bsd6vaz8e%2BjACC74kL3m0Cylj70IvbBZC6WcarJJTRVP8OnWoYySDJyL12aryggK8pQrs9M2h8MAKOtOk4efKRbiiXXPIZyH%2FDpmNu2Rs3tEPrV0ZTODsb7JQtrMqSgEftbsAH7BzOjoMAlJ0J%2FkIR1fs3ubYsnkc7SFve%2F1dFJAD1ki2mh2Iwb%2Blyd%2FJC0U9tt5rrM5y6BzAP24UqIOxrOfyV5D1VfDMsZ0r88db9CMAHKpwjpH1jfkTdR4IpncwRSG7kuOXn92BNwDKuq3Cmu6IoLtK3zLKQzZ9hrlnUuMbkwqYWgHhGDiQdCgKhpD%2Fjt1BH2riF%2B89Y9NFysqWgdM9nytqF3URaLxM0FcEXwtUi%2FIYU6lKYueCfFDuywxl3T1PQ6PKMjF5qtMG%2FJ0PUtQjclakIAMhV9Her%2Fzx7tnRX5HDZdF0lzSTbcHPZgN3egubK2W4OhaOtpK48E85YH6OfOfhXYrHrOMrn5zP6RXDdSraAPJeAtUyLHdyYURiPAujaDFYpGd4uG3rW37iF1PhhFLSYOl4ACRdqRTPDEYv43n9HtEaGrv3oqGxTeLV7FZRw%2Bjwfyd0TNRrzUnl5nGHY8drMVcHr4J1JGCgQbmAD3AXvHqfrSZilUg8go9F5jI5SRBrlJAFSjzxOznwToySIsA%2B04wAtDVkzU00XIfpn08W9l%2FZfhY%2B2JtkmfzDKqK42qNmUpcSwi7%2FIRAO1p2nZsFtEl7HaqIQcIat%2FLoCFtkqwr7CYFVoCGOyQDoZPp8wAGaVKzD0fKTIkc7YuGq7VULA1p6o2IWAinpDwg720zBf8CUKX7%2F%2BHB348O%2B7NlJM5gOooDTuovIDRG%2FF8INV2UwWJJECgLkgPV4Sqd5mW%2B%2F43VDeCHRyPBWbUFRhWScTsgQynPg%3D%3D&nvMid=53392390390&catId=50000807"
]

# 2) Output filename: IMAGE_NAME_PREFIX + number + IMAGE_EXTENSION
# Example: IMAGE_NAME_PREFIX = "content_zigzag_", START_NUMBER = 1
#          -> content_zigzag_1.png
IMAGE_NAME_PREFIX = "콘텐츠_1_지그재그_"
IMAGE_EXTENSION = ".png"

# 3) Number range. The number increases by 1 from START_NUMBER to END_NUMBER.
# The URL count must match this number count.
START_NUMBER = 3
END_NUMBER = 9

# 4) Images are saved in the same Framework folder as this script.
OUTPUT_DIR = Path(__file__).resolve().parent

# 5) Browser/page settings.
VIEWPORT_WIDTH = 1920
VIEWPORT_HEIGHT = 1080
PAGE_LOAD_TIMEOUT_MS = 60000
WAIT_AFTER_LOAD_MS = 1500


def validate_settings() -> list[int]:
    numbers = list(range(START_NUMBER, END_NUMBER + 1))

    if not LINKS:
        raise ValueError("Add at least one URL to LINKS.")

    if len(LINKS) != len(numbers):
        raise ValueError(
            "LINKS count must match the START_NUMBER..END_NUMBER count. "
            f"Current LINKS={len(LINKS)}, numbers={len(numbers)}."
        )

    if not IMAGE_EXTENSION.startswith("."):
        raise ValueError('IMAGE_EXTENSION must start with a dot, like ".png".')

    return numbers


def capture_pages() -> None:
    numbers = validate_settings()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(
            viewport={"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT},
            device_scale_factor=1,
        )

        for url, number in zip(LINKS, numbers):
            output_path = OUTPUT_DIR / f"{IMAGE_NAME_PREFIX}{number}{IMAGE_EXTENSION}"
            print(f"[capture] {url} -> {output_path.name}")

            try:
                page.goto(url, wait_until="networkidle", timeout=PAGE_LOAD_TIMEOUT_MS)
            except PlaywrightTimeoutError:
                print("[warn] Timed out waiting for networkidle. Capturing the loaded page.")

            page.wait_for_timeout(WAIT_AFTER_LOAD_MS)
            page.screenshot(path=str(output_path), full_page=True)

        browser.close()


if __name__ == "__main__":
    capture_pages()
