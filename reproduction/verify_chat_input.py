from playwright.sync_api import sync_playwright
import time

def test_chat_input_population():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto("http://0.0.0.0:8502", timeout=60000)
            page.wait_for_selector("button:has-text('Question 1')", timeout=60000)

            # Click the first related question
            page.click("button:has-text('Question 1')")

            # Wait for reload
            page.wait_for_timeout(2000)

            # Check if chat input has the value
            # The chat input in streamlit is a textarea.
            # We can check the value property.
            input_val = page.locator("textarea[aria-label='Type something...']").input_value()
            print(f"Input value after click: '{input_val}'")

            if input_val == "Question 1":
                print("SUCCESS: Input populated.")
            else:
                print("FAILURE: Input not populated.")

            page.screenshot(path="/home/jules/verification/chat_input_test.png")

        except Exception as e:
            print(f"Error: {e}")
            page.screenshot(path="/home/jules/verification/chat_input_error.png")
        finally:
            browser.close()

if __name__ == "__main__":
    test_chat_input_population()
