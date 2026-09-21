# Nhãn tham chiếu và đo nhận diện

Precision/recall **chỉ** được tính khi có bộ nhãn do người gán, kèm tên người
gán. Công cụ không bịa accuracy.

## Rubric tối thiểu (người gán phải ghi)

Đánh trên chart, nến đã đóng:

* `SWING_HIGH` / `SWING_LOW` — đỉnh/đáy mắt thường theo cùng ý tưởng cửa sổ
  pivot (không nhìn tương lai khi gán cho thí nghiệm online; nếu gán hồi cứu
  phải ghi rõ trong rubric).
* `SWING_HIGH_L2` / `SWING_LOW_L2` — đỉnh/đáy cấp 2 (lọc trên chuỗi pivot cấp 1),
  nếu thí nghiệm dùng `swing_hierarchy`.
* `BOS_UP` / `BOS_DOWN` — phá cấu trúc chính theo close.
* `BOS_INTERNAL_*` — phá đỉnh/đáy hồi, chưa phá mức chính.
* `CHOCH_*` — đổi hướng, phá HL/LH đang định nghĩa bias.

## Quy tắc ghép (`core/labels.py`)

* Cùng `structure_type` (không gộp BOS nội bộ với BOS chính).
* `|Δ nến| ≤ time_tolerance_bars` (mặc định 1).
* `|Δ giá| ≤ price_tolerance` (mặc định 0).
* Ghép tham lam 1-1, ưu tiên Δnến rồi Δgiá.

Precision = TP/(TP+FP), Recall = TP/(TP+FN). Bộ nhãn trống → không ra số.

## API

* `POST /api/label-sets` — tạo bộ (dataset_id, annotator, version, rubric_vi, labels[])
* `GET /api/label-sets?dataset_id=`
* `POST /api/evaluate` — `{run_id, label_set_id, time_tolerance_bars, price_tolerance}`
