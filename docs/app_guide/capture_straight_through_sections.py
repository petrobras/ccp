#!/usr/bin/env python3
"""
Final working script for capturing Straight Through app section screenshots.
This script reloads the page for each section to ensure correct captures with proper header positioning.

Usage: python capture_straight_through_sections.py
Requirements: playwright, streamlit app running on localhost:8502
"""

from playwright.sync_api import sync_playwright
from pathlib import Path
import time
import os

images_dir = Path(__file__).parent / "images"
images_dir.mkdir(parents=True, exist_ok=True)


def capture_section(page, section_name, filename):
    """Capture a specific section with fresh page state"""
    try:
        print(f"Capturing {section_name}...")

        # Reload page to get fresh state
        page.goto("http://localhost:8502", timeout=30000)
        page.wait_for_load_state("networkidle", timeout=30000)
        time.sleep(5)  # Wait for Streamlit to fully load

        # Find and expand the specific section
        result = page.evaluate(f"""
            () => {{
                // Find all summary elements
                const summaries = document.querySelectorAll('details summary');
                let targetSummary = null;

                for (let summary of summaries) {{
                    if (summary.textContent.includes('{section_name}')) {{
                        targetSummary = summary;
                        break;
                    }}
                }}

                if (!targetSummary) return {{ found: false }};

                // Click to expand the section
                targetSummary.click();

                return {{ found: true }};
            }}
        """)

        if not result["found"]:
            print(f"Could not find {section_name}")
            return False

        time.sleep(3)  # Wait for expansion animation

        # Position the expanded section at the top
        scroll_result = page.evaluate(f"""
            () => {{
                const summaries = document.querySelectorAll('details summary');
                let targetSummary = null;

                for (let summary of summaries) {{
                    if (summary.textContent.includes('{section_name}')) {{
                        targetSummary = summary;
                        break;
                    }}
                }}

                if (!targetSummary) return {{ success: false }};

                // Get element's position
                const rect = targetSummary.getBoundingClientRect();
                const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
                const elementTop = rect.top + scrollTop;

                // Scroll so header appears at top of viewport
                window.scrollTo(0, Math.max(0, elementTop - 10));

                return {{
                    success: true,
                    scrolledTo: Math.max(0, elementTop - 10)
                }};
            }}
        """)

        if scroll_result["success"]:
            time.sleep(2)  # Wait for scroll

            # Take screenshot
            page.screenshot(path=images_dir / filename)
            print(f"Successfully captured {section_name}")
            return True
        else:
            print(f"Failed to position {section_name}")
            return False

    except Exception as e:
        print(f"Error capturing {section_name}: {e}")
        return False


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()

        try:
            # First, capture the main interface
            print("Capturing main interface...")
            page.goto("http://localhost:8502", timeout=30000)
            page.wait_for_load_state("networkidle", timeout=30000)
            time.sleep(5)
            page.screenshot(path=images_dir / "straight_through_01_main.png")
            print("Captured main interface")

            # Define sections to capture - each gets a fresh page load
            sections = [
                ("Gas Selection", "straight_through_02_gas_selection.png"),
                ("Data Sheet", "straight_through_03_data_sheet.png"),
                ("Curves", "straight_through_04_curves.png"),
                ("Test Data", "straight_through_05_test_data.png"),
                (
                    "Flowrate Calculation",
                    "straight_through_06_flowrate_calculation.png",
                ),
            ]

            # Capture each section with fresh page state
            for section_name, filename in sections:
                success = capture_section(page, section_name, filename)
                if not success:
                    print(f"Failed to capture {section_name}")

            print("Screenshot capture complete!")

        except Exception as e:
            print(f"Error: {e}")
        finally:
            browser.close()


if __name__ == "__main__":
    main()
