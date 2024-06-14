import re


def bounds_to_coords(bounds_string):
    pattern = r"\[(-?\d+),(-?\d+)\]\[(-?\d+),(-?\d+)\]"
    matches = re.findall(pattern, bounds_string)
    return list(map(int, matches[0]))


def coords_to_bounds(bounds):
    return f"[{bounds[0]},{bounds[1]}][{bounds[2]},{bounds[3]}]"


def check_valid_bounds(bounds):
    bounds = bounds_to_coords(bounds)

    return 0 <= bounds[0] < bounds[2] and 0 <= bounds[1] < bounds[3]


def check_bounds_containing(bounds_contained, bounds_containing):
    bounds_contained = bounds_to_coords(bounds_contained)
    bounds_containing = bounds_to_coords(bounds_containing)

    return bounds_contained[0] >= bounds_containing[0] and \
        bounds_contained[1] >= bounds_containing[1] and \
        bounds_contained[2] <= bounds_containing[2] and \
        bounds_contained[3] <= bounds_containing[3]


def check_bounds_intersection(bounds1, bounds2):
    bounds1 = bounds_to_coords(bounds1)
    bounds2 = bounds_to_coords(bounds2)

    return bounds1[0] < bounds2[2] and bounds1[2] > bounds2[0] and \
        bounds1[1] < bounds2[3] and bounds1[3] > bounds2[1]


def compare_bounds_size(bounds1, bounds2):
    """
    :return:
        if bounds1 is smaller than bounds2, return true
        else return false
    """
    bounds1 = bounds_to_coords(bounds1)
    bounds2 = bounds_to_coords(bounds2)

    return (bounds1[2] - bounds1[0]) * (bounds1[3] - bounds1[1]) < \
        (bounds2[2] - bounds2[0]) * (bounds2[3] - bounds2[1])


def compare_y_in_bounds(bounds1, bounds2):
    """
    :return:
        if y in bounds1 is smaller than that in bounds2, return true
        else return false
    """
    bounds1 = bounds_to_coords(bounds1)
    bounds2 = bounds_to_coords(bounds2)

    return bounds1[1] < bounds2[1] and bounds1[3] < bounds2[3]


class MiniMapSpecialCheck:
    def __init__(self, xml_string, root):
        self.xml_string = xml_string
        self.root = root

    def check(self):
        page, page_type = self.check_page()
        if page == "filter":
            self.base_node = None
            self.retrieve_times = 0
            self.recycler_node = None
            self.recycler_bounds = "[0,0][0,0]"
            self.check_filter(page_type)
        elif page == "route":
            self.base_node = None
            self.check_route()

    def check_page(self):
        page_map = {
            "filter": [
                (["距离优先", "推荐排序", "好评优先"], "推荐排序"),
                (["距离", "km内"], "位置距离"),
                (["烤肉", "烧烤", "螺蛳粉"], "全部分类"),
                (["烤肉", "烧烤", "蛋糕店"], "全部分类"),
                (["水产海鲜", "火锅", "熟食"], "全部分类"),
                (["水产海鲜", "火锅", "早餐"], "全部分类"),
                (["星级(可多选)", "价格"], "星级酒店"),
                (["品牌", "宾客类型", "特色主题"], "更多筛选"),
                (["92#", "95#", "98#", "0#"], "油类型"),
                (["全部品牌", "中国石化", "中国石油", "壳牌"], "全部品牌")
            ],
            "route": [
                (["驾车", "火车", "步行", "收起"], None)
            ]
        }

        for key, values in page_map.items():
            for keywords, page_type in values:
                if all(k in self.xml_string for k in keywords):
                    return key, page_type
        return None, None

    def get_filter_base_node(self, node, page_type):
        page_criteria = {
            "推荐排序": [("距离优先", 14)],
            "位置距离": [("km内", 8)],
            "全部分类": [("烤肉", 14), ("火锅", 14)],
            "星级酒店": [("星级(可多选)", 10)],
            "更多筛选": [("品牌", 9)],
            "全部品牌": [("全部品牌", 14)],
            "油类型": [("95#", 14)]
        }

        pattern_need_fuzzy = ["km内"]

        if 'content-desc' in node.attrib:
            for pattern, retrieve_times in page_criteria.get(page_type, []):
                content_desc = node.attrib['content-desc']
                text = node.attrib['text']
                # find the specialCheck base node
                if (pattern in pattern_need_fuzzy and (pattern in content_desc or pattern in text)) or \
                        (pattern not in pattern_need_fuzzy and (pattern == content_desc or pattern == text)):
                    # If the base node is not unique, find the one that is lower.
                    if self.base_node is None or compare_y_in_bounds(self.base_node.attrib['bounds'],
                                                                     node.attrib['bounds']):
                        self.base_node = node
                        self.retrieve_times = retrieve_times
                        break

        # Find a node that can scroll in a loop.
        if 'RecyclerView' in node.attrib.get('class', '') and 'true' in node.attrib.get('scrollable', ''):
            # If the node is not unique, find the one that is larger.
            if compare_bounds_size(self.recycler_bounds, node.attrib['bounds']):
                self.recycler_node = node
                self.recycler_bounds = node.attrib['bounds']

        for child in list(node):
            self.get_filter_base_node(child, page_type)

    def check_filter(self, page_type):
        self.get_filter_base_node(self.root, page_type)
        node = self.base_node
        if node is None:
            return

        while self.retrieve_times > 0:
            if node.getparent() is not None:
                node = node.getparent()
                self.retrieve_times -= 1
            else:
                return

        parent = node.getparent()
        if parent is not None:
            delete_ind = parent.index(node) + 1
            try:
                parent.remove(list(parent)[delete_ind])
                parent.remove(list(parent)[delete_ind])
            except Exception:
                pass

        if self.recycler_node.getparent() is not None:
            self.recycler_node.getparent().remove(self.recycler_node)

    def get_route_base_node(self, node):
        if 'content-desc' in node.attrib and ("收起" == node.attrib['content-desc'] or "收起" == node.attrib['text']):
            self.base_node = node

        for child in list(node):
            self.get_route_base_node(child)

    def check_route(self):
        self.get_route_base_node(self.root)
        node = self.base_node
        if node is None:
            return

        times = 2
        for _ in range(times):
            if node.getparent() is not None:
                node = node.getparent()

        parent = node.getparent()
        for ind, child in reversed(list(enumerate(parent))):
            if child != node:
                parent.remove(child)


SpecialCheck = {
    "com.autonavi.minimap": MiniMapSpecialCheck,
}
