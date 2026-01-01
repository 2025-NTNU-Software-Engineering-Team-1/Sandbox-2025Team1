import heapq
import json
import sys
import urllib.request

BASE_URL = "http://local_service:8080/api/answers?page="


def fetch_page(page):
    url = f"{BASE_URL}{page}"
    with urllib.request.urlopen(url, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def k_way_merge(sorted_lists):
    heap = []
    for list_idx, items in enumerate(sorted_lists):
        if items:
            score, sid = items[0]
            heapq.heappush(heap, (score, sid, list_idx, 0))

    result = []
    while heap:
        score, sid, list_idx, elem_idx = heapq.heappop(heap)
        result.append(sid)
        next_idx = elem_idx + 1
        if next_idx < len(sorted_lists[list_idx]):
            next_score, next_id = sorted_lists[list_idx][next_idx]
            heapq.heappush(heap, (next_score, next_id, list_idx, next_idx))
    return result


def main():
    first_page = fetch_page(1)
    total_pages = int(first_page.get("total_pages", 0))

    pages = []
    pages.append([(item["score"], item["id"])
                  for item in first_page.get("data", [])])

    for page in range(2, total_pages + 1):
        payload = fetch_page(page)
        pages.append([(item["score"], item["id"])
                      for item in payload.get("data", [])])

    merged = k_way_merge(pages)
    output = [str(len(merged))] + [str(sid) for sid in merged]
    sys.stdout.write("\n".join(output) + "\n")


if __name__ == "__main__":
    main()
