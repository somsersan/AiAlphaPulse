import webbrowser
import os
import sys


def open_html_page():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    html_file = os.path.join(current_dir, 'index.html')

    if not os.path.exists(html_file):
        return False

    webbrowser.open(f'file://{html_file}')
    return True


if __name__ == "__main__":
    open_html_page()