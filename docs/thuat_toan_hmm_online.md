# HMM lọc online (`hmm_online` v1.0.0)

**File:** [`core/algorithms/hmm_online.py`](../core/algorithms/hmm_online.py)

## Tách fit và lọc — bắt buộc

* **Fit:** `GaussianHMM` (hmmlearn), `covariance_type=diag`, chỉ trên
  `train_bars` nến đầu. Chạy khi nến thứ `train_bars` đóng, **một lần**.
* **`on_bar` sau đó:** chỉ bước **forward** (lọc) với `startprob_`, `transmat_`,
  `means_`, `covars_` đã đóng băng. Không gọi `predict` / `score` trên toàn
  chuỗi, không Viterbi, không forward-backward smoothing.
* Sự kiện chỉ phát khi nến có `index >= train_bars` (mốc `model_usable_from`).
  Prefix train không được gắn state như tín hiệu online.

Seed, `train_bars`, `n_iter` lưu trong tham số lần chạy.

## Feature (tính trên nến đóng)

```
r_t     = log(close_t / close_{t-1})   (0 ở nến đầu)
|r_t|
(high_t − low_t) / |close_t|
```

## Ánh xạ state

Tham số `state_map` dạng `0=chua_gan_nghia,1=chua_gan_nghia,2=chua_gan_nghia`.
**Mặc định không gắn Trend/Range.** Đổi map là quyết định nghiên cứu, phải ghi
vào lần chạy.

## Warm-up

`warmup_bars = train_bars`. Chuỗi ngắn hơn → `WARMUP_INSUFFICIENT`.

## Giới hạn

* hmmlearn ở chế độ limited-maintenance; ghim phiên bản trong lockfile khi dùng.
* Fit trên cùng dữ liệu rồi lọc tiếp là in-sample trên prefix — không phải
  walk-forward đầy đủ. Muốn walk-forward: cắt dataset, tăng `train_bars` theo
  từng fold, chạy lại.
* Không có lịch refit tự động trong `on_bar`.
