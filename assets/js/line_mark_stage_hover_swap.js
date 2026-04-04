<script>
(function applyStageHoverSwap() {
  const thinUrl = __THIN_IMAGE_URL__;
  const thickUrl = __THICK_IMAGE_URL__;
  if (!thinUrl || !thickUrl) return;
  const images = Array.from(window.parent.document.querySelectorAll('div[data-testid="stImage"] img'));
  if (!images.length) return;
  const pointer = window.parent.__lineMarkLastPointer;
  const pickTargetImage = () => {
    if (pointer) {
      const underPointer = images.find((candidate) => {
        const rect = candidate.getBoundingClientRect();
        return pointer.x >= rect.left && pointer.x <= rect.right && pointer.y >= rect.top && pointer.y <= rect.bottom;
      });
      if (underPointer) return underPointer;
    }
    return images
      .slice()
      .sort((left, right) => (right.clientWidth * right.clientHeight) - (left.clientWidth * left.clientHeight))[0];
  };
  const target = pickTargetImage();
  if (!target) return;
  if (window.parent.__lineMarkHoverSwapEnter) {
    target.removeEventListener("mouseenter", window.parent.__lineMarkHoverSwapEnter, true);
  }
  if (window.parent.__lineMarkHoverSwapLeave) {
    target.removeEventListener("mouseleave", window.parent.__lineMarkHoverSwapLeave, true);
  }
  const isInsideTarget = (clientX, clientY) => {
    const rect = target.getBoundingClientRect();
    return clientX >= rect.left && clientX <= rect.right && clientY >= rect.top && clientY <= rect.bottom;
  };
  const applyFromPointer = () => {
    const currentPointer = window.parent.__lineMarkLastPointer;
    if (currentPointer && isInsideTarget(currentPointer.x, currentPointer.y)) {
      target.src = thinUrl;
      return;
    }
    target.src = thickUrl;
  };
  window.parent.__lineMarkHoverSwapEnter = () => { target.src = thinUrl; };
  window.parent.__lineMarkHoverSwapLeave = () => { target.src = thickUrl; };
  const oldPointerTracker = window.parent.__lineMarkPointerTracker;
  if (oldPointerTracker) {
    window.parent.document.removeEventListener("mousemove", oldPointerTracker, true);
  }
  window.parent.__lineMarkPointerTracker = (event) => {
    window.parent.__lineMarkLastPointer = { x: event.clientX, y: event.clientY };
  };
  window.parent.document.addEventListener("mousemove", window.parent.__lineMarkPointerTracker, true);
  target.addEventListener("mouseenter", window.parent.__lineMarkHoverSwapEnter, true);
  target.addEventListener("mouseleave", window.parent.__lineMarkHoverSwapLeave, true);
  applyFromPointer();
})();
</script>
