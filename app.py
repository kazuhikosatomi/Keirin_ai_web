def extract_lineinfo_from_url(url):
    import requests
    from bs4 import BeautifulSoup

    try:
        r = requests.get(url)
        soup = BeautifulSoup(r.text, 'html.parser')
        square_spans = soup.select('span.square-slim')
        groups = []
        current_group = []

        for span in square_spans:
            num = span.text.strip()
            if num:
                current_group.append(num)
            next_sibling = span.find_next_sibling()
            if next_sibling and 'p10' in next_sibling.get('class', []):
                groups.append(current_group)
                current_group = []
        if current_group:
            groups.append(current_group)

        lineinfo_dict = {}
        for line_id, group in enumerate(groups, start=1):
            for line_pos, car_number in enumerate(group, start=1):
                lineinfo_dict[car_number] = {
                    "line_id": str(line_id),
                    "line_pos": str(line_pos)
                }
        return lineinfo_dict
    except Exception as e:
        print(f"[ERROR] extract_lineinfo_from_url: {e}")
        return {}