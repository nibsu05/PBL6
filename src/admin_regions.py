"""Ánh xạ tỉnh cũ (tên trong FAO GAUL 2015, cấp 1) sang 34 tỉnh/thành mới (NQ 202/2025/QH15).

Mỗi tỉnh mới là hợp *trọn vẹn* của các tỉnh cũ, nên gán ô lưới theo ranh giới cũ
rồi đổi tên là chính xác. 11 đơn vị không sắp xếp giữ tên; "Ha Tay" (đã nhập Hà Nội
từ 2008) vẫn còn trong GAUL 2015.
"""

from __future__ import annotations

OLD_TO_NEW: dict[str, str] = {
    # Không sắp xếp
    "Cao Bang": "Cao Bằng", "Dien Bien": "Điện Biên", "Ha Tinh": "Hà Tĩnh", "Lai Chau": "Lai Châu",
    "Lang Son": "Lạng Sơn", "Nghe An": "Nghệ An", "Quang Ninh": "Quảng Ninh", "Thanh Hoa": "Thanh Hóa",
    "Son La": "Sơn La", "Ha Noi City": "Hà Nội", "Ha Tay": "Hà Nội", "Thua Thien - Hue": "Huế",
    # Sắp xếp
    "Tuyen Quang": "Tuyên Quang", "Ha Giang": "Tuyên Quang",
    "Lao Cai": "Lào Cai", "Yen Bai": "Lào Cai",
    "Thai Nguyen": "Thái Nguyên", "Bac Kan": "Thái Nguyên",
    "Phu Tho": "Phú Thọ", "Vinh Phuc": "Phú Thọ", "Hoa Binh": "Phú Thọ",
    "Bac Ninh": "Bắc Ninh", "Bac Giang": "Bắc Ninh",
    "Hung Yen": "Hưng Yên", "Thai Binh": "Hưng Yên",
    "Hai Phong City": "Hải Phòng", "Hai Duong": "Hải Phòng",
    "Ninh Binh": "Ninh Bình", "Ha Nam": "Ninh Bình", "Nam Dinh": "Ninh Bình",
    "Quang Tri": "Quảng Trị", "Quang Binh": "Quảng Trị",
    "Da Nang City": "Đà Nẵng", "Quang Nam": "Đà Nẵng",
    "Quang Ngai": "Quảng Ngãi", "Kon Tum": "Quảng Ngãi",
    "Gia Lai": "Gia Lai", "Binh Dinh": "Gia Lai",
    "Khanh Hoa": "Khánh Hòa", "Ninh Thuan": "Khánh Hòa",
    "Lam Dong": "Lâm Đồng", "Dak Nong": "Lâm Đồng", "Binh Thuan": "Lâm Đồng",
    "Dak Lak": "Đắk Lắk", "Phu Yen": "Đắk Lắk",
    "Ho Chi Minh City": "TP.HCM", "Binh Duong": "TP.HCM", "Ba Ria-Vung Tau": "TP.HCM",
    "Dong Nai": "Đồng Nai", "Binh Phuoc": "Đồng Nai",
    "Tay Ninh": "Tây Ninh", "Long An": "Tây Ninh",
    "Can Tho city": "Cần Thơ", "Soc Trang": "Cần Thơ", "Hau Giang": "Cần Thơ",
    "Vinh Long": "Vĩnh Long", "Ben Tre": "Vĩnh Long", "Tra Vinh": "Vĩnh Long",
    "Dong Thap": "Đồng Tháp", "Tien Giang": "Đồng Tháp",
    "Ca Mau": "Cà Mau", "Bac Lieu": "Cà Mau",
    "An Giang": "An Giang", "Kien Giang": "An Giang",
}

NEW_PROVINCES = sorted(set(OLD_TO_NEW.values()))
assert len(NEW_PROVINCES) == 34, len(NEW_PROVINCES)
