import uuid

def get_cool_random_name() -> str:
    """
    Generates a unique random name.
    TODO: The original TypeScript version used 'get-cool-random-name' library.
    This is a placeholder using UUID.
    """
    return str(uuid.uuid4())

def generate_home_html(link_expiry_ms: int) -> str:
    """
    Generates the HTML content for the home page.
    Args:
        link_expiry_ms: The duration in milliseconds for which links are valid.
    Returns:
        An HTML string for the home page.
    """
    minutes = link_expiry_ms // 60000
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>File Upload Service</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; background-color: #f0f2f5; color: #333; text-align: center; }}
        h1 {{ color: #4a4a4a; }}
        p {{ font-size: 1.1em; color: #555; }}
        .container {{ background-color: #fff; padding: 30px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); display: inline-block; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Welcome to the FastAPI File Upload Service!</h1>
        <p>Links to uploaded files are valid for {minutes} minutes.</p>
        <p>Use the <code>/upload</code> endpoint to upload files and <code>/file/{{id}}</code> to download them.</p>
    </div>
</body>
</html>
"""

if __name__ == "__main__":
    # Test get_cool_random_name
    random_name1 = get_cool_random_name()
    random_name2 = get_cool_random_name()
    print(f"Generated random name 1: {random_name1}")
    print(f"Generated random name 2: {random_name2}")
    assert random_name1 != random_name2
    assert isinstance(random_name1, str)

    # Test generate_home_html
    expiry_ms = 3600000  # 60 minutes
    html_output = generate_home_html(expiry_ms)
    print("\nGenerated HTML:")
    print(html_output)
    assert f"valid for {expiry_ms // 60000} minutes" in html_output
    assert "<!DOCTYPE html>" in html_output
    assert "FastAPI File Upload Service" in html_output

    expiry_ms_short = 300000 # 5 minutes
    html_output_short = generate_home_html(expiry_ms_short)
    print("\nGenerated HTML (short expiry):")
    print(html_output_short)
    assert f"valid for {expiry_ms_short // 60000} minutes" in html_output_short

    print("\n--- misc_utils tests completed ---")
