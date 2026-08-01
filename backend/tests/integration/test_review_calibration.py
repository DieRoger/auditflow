"""Verify ReviewCalibration — Accepted Finding Rate (HITL quality)"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src')))

from application.assessment.review_queue import (
    ReviewQueue, ReviewItem, ReviewDecision, ReviewCalibration,
)

# 模拟 30 条 finding 的复核: 初始接受 20/30 (67%), 校准后 25/30 (83%)
queue = ReviewQueue()
for i in range(30):
    item = ReviewItem(item_id=f"rv_{i:03d}", area="Revenue", risk_level="MEDIUM", summary=f"Finding {i}")
    if i < 20:
        item.review(ReviewDecision.ACCEPT, "Looks valid")
    elif i < 24:
        item.review(ReviewDecision.DISMISS, "Business normal")
    else:
        item.review(ReviewDecision.NEED_MORE_EVIDENCE, "Need delivery note")
    queue.add(item)

rate = ReviewCalibration.accepted_finding_rate(queue)
dist = ReviewCalibration.decision_distribution(queue)
print(f"Accepted Finding Rate: {rate:.0f}%")
print(f"Distribution: {dist}")
assert abs(rate - 66.7) < 0.1, f"expected ~66.7%, got {rate}"

# 校准演示
cal = ReviewCalibration.simulate_calibration(20, 30, 25, 30)
print(f"Calibration: {cal['before_pct']}% -> {cal['after_pct']}% (improvement +{cal['improvement']}pp)")
assert cal["before_pct"] == 66.7 and cal["after_pct"] == 83.3

print("\nOK: ReviewCalibration works — Accepted Finding Rate is measurable")
