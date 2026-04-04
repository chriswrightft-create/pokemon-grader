<script>
(function applyStageImageZoom() {
  const zoomFactor = __ZOOM_FACTOR__;
  window.parent.__lineMarkZoomMode = "stage";
  const canvasMove = window.parent.__lineMarkMoveHandler;
  const canvasDown = window.parent.__lineMarkDownHandler;
  const canvasUp = window.parent.__lineMarkUpHandler;
  const frames = window.parent.document.querySelectorAll("iframe");
  frames.forEach((frame) => {
    try {
      const doc = frame.contentDocument || frame.contentWindow.document;
      if (!doc) return;
      if (canvasMove) doc.removeEventListener("mousemove", canvasMove, true);
      if (canvasDown) doc.removeEventListener("mousedown", canvasDown, true);
      if (canvasUp) doc.removeEventListener("mouseup", canvasUp, true);
    } catch (error) {}
  });
  const panelId = "line-mark-side-zoom";
  const panelCanvasId = "line-mark-side-zoom-canvas";
  let panel = window.parent.document.getElementById(panelId);
  let panelCanvas = window.parent.document.getElementById(panelCanvasId);
  if (!panel || !panelCanvas) {
    panel = window.parent.document.createElement("div");
    panel.id = panelId;
    panel.style.position = "fixed";
    panel.style.right = "12px";
    panel.style.top = "12px";
    panel.style.width = "170px";
    panel.style.height = "170px";
    panel.style.border = "1px solid #00ffff";
    panel.style.background = "rgba(0,0,0,0.72)";
    panel.style.borderRadius = "8px";
    panel.style.zIndex = "2147483647";
    panel.style.pointerEvents = "none";
    panel.style.display = "none";
    panelCanvas = window.parent.document.createElement("canvas");
    panelCanvas.id = panelCanvasId;
    panelCanvas.width = 168;
    panelCanvas.height = 168;
    panelCanvas.style.width = "168px";
    panelCanvas.style.height = "168px";
    panelCanvas.style.display = "block";
    panel.appendChild(panelCanvas);
    window.parent.document.body.appendChild(panel);
  }

  const ctx = panelCanvas.getContext("2d");
  if (!ctx) return;
  const zoom = zoomFactor;
  const radius = 30;

  const drawAt = (event) => {
    if (!event || typeof event.clientX !== "number" || typeof event.clientY !== "number") {
      panel.style.display = "none";
      return;
    }
    const images = Array.from(window.parent.document.querySelectorAll('div[data-testid="stImage"] img'));
    if (!images.length) {
      panel.style.display = "none";
      return;
    }
    const targetImage = images.find((imageNode) => {
      const rect = imageNode.getBoundingClientRect();
      return event.clientX >= rect.left && event.clientX <= rect.right && event.clientY >= rect.top && event.clientY <= rect.bottom;
    });
    if (!targetImage) {
      panel.style.display = "none";
      return;
    }
    const rect = targetImage.getBoundingClientRect();
    if (!targetImage.complete || (typeof targetImage.naturalWidth === "number" && targetImage.naturalWidth <= 0)) {
      const pendingPointer = window.parent.__lineMarkLastPointer;
      const handleLoaded = () => {
        const pointer = window.parent.__lineMarkLastPointer || pendingPointer;
        if (pointer && typeof pointer.x === "number" && typeof pointer.y === "number") {
          drawAt({ clientX: pointer.x, clientY: pointer.y });
        }
      };
      targetImage.addEventListener("load", handleLoaded, { once: true });
      return;
    }
    const clearButton = Array.from(window.parent.document.querySelectorAll("button")).find(
      (button) => (button.textContent || "").trim().toLowerCase() === "clear marked points"
    );
    const controlsLeft = clearButton ? clearButton.getBoundingClientRect().left : null;
    if (controlsLeft !== null) {
      const gapWidth = Math.max(0, controlsLeft - rect.right);
      const gapLeft = rect.right;
      const centeredLeft = Math.round(gapLeft + Math.max(0, (gapWidth - panelCanvas.width) / 2));
      panel.style.left = `${centeredLeft}px`;
    } else {
      panel.style.left = `${Math.round(rect.right + 12)}px`;
    }
    panel.style.top = `${Math.round(rect.top)}px`;
    panel.style.right = "auto";
    const naturalWidth = Math.max(1, targetImage.naturalWidth || rect.width || 1);
    const naturalHeight = Math.max(1, targetImage.naturalHeight || rect.height || 1);
    const boxWidth = Math.max(1, rect.width);
    const boxHeight = Math.max(1, rect.height);
    const imageAspect = naturalWidth / naturalHeight;
    const boxAspect = boxWidth / boxHeight;
    let renderedWidth = boxWidth;
    let renderedHeight = boxHeight;
    if (boxAspect > imageAspect) {
      renderedHeight = boxHeight;
      renderedWidth = renderedHeight * imageAspect;
    } else {
      renderedWidth = boxWidth;
      renderedHeight = renderedWidth / imageAspect;
    }
    const renderedLeft = (boxWidth - renderedWidth) / 2;
    const renderedTop = (boxHeight - renderedHeight) / 2;
    const localX = event.clientX - rect.left;
    const localY = event.clientY - rect.top;
    const imageLocalX = localX - renderedLeft;
    const imageLocalY = localY - renderedTop;
    const insideRenderedImage =
      imageLocalX >= 0 &&
      imageLocalX <= renderedWidth &&
      imageLocalY >= 0 &&
      imageLocalY <= renderedHeight;
    if (!insideRenderedImage) {
      panel.style.display = "none";
      return;
    }
    panel.style.display = "block";
    const normalizedX = imageLocalX / Math.max(1, renderedWidth);
    const normalizedY = imageLocalY / Math.max(1, renderedHeight);
    const sxScale = naturalWidth / Math.max(1, renderedWidth);
    const syScale = naturalHeight / Math.max(1, renderedHeight);
    const sample = (radius * 2) / zoom;
    const sampleX = normalizedX * naturalWidth;
    const sampleY = normalizedY * naturalHeight;
    const sampleW = Math.max(2, sample * sxScale);
    const sampleH = Math.max(2, sample * syScale);
    const srcX = sampleX - sampleW / 2;
    const srcY = sampleY - sampleH / 2;
    const srcX0 = Math.max(0, srcX);
    const srcY0 = Math.max(0, srcY);
    const srcX1 = Math.min(naturalWidth, srcX + sampleW);
    const srcY1 = Math.min(naturalHeight, srcY + sampleH);
    const srcW = Math.max(0, srcX1 - srcX0);
    const srcH = Math.max(0, srcY1 - srcY0);
    ctx.clearRect(0, 0, panelCanvas.width, panelCanvas.height);
    ctx.fillStyle = "rgba(0,0,0,0.55)";
    ctx.fillRect(0, 0, panelCanvas.width, panelCanvas.height);
    ctx.imageSmoothingEnabled = false;
    if (srcW > 0 && srcH > 0) {
      ctx.drawImage(
        targetImage,
        srcX0,
        srcY0,
        srcW,
        srcH,
        (Math.max(0, srcX0 - srcX) / sampleW) * panelCanvas.width,
        (Math.max(0, srcY0 - srcY) / sampleH) * panelCanvas.height,
        (srcW / sampleW) * panelCanvas.width,
        (srcH / sampleH) * panelCanvas.height
      );
    }
    ctx.strokeStyle = "#00ffff";
    ctx.lineWidth = 1;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.beginPath();
    ctx.moveTo(panelCanvas.width / 2 - 10, panelCanvas.height / 2);
    ctx.lineTo(panelCanvas.width / 2 + 10, panelCanvas.height / 2);
    ctx.moveTo(panelCanvas.width / 2, panelCanvas.height / 2 - 10);
    ctx.lineTo(panelCanvas.width / 2, panelCanvas.height / 2 + 10);
    ctx.stroke();
  };

  const oldMove = window.parent.__lineMarkStageMove;
  if (oldMove) window.parent.document.removeEventListener("mousemove", oldMove, true);
  const oldPointerTracker = window.parent.__lineMarkPointerTracker;
  if (oldPointerTracker) {
    window.parent.document.removeEventListener("mousemove", oldPointerTracker, true);
  }
  window.parent.__lineMarkPointerTracker = (event) => {
    window.parent.__lineMarkLastPointer = { x: event.clientX, y: event.clientY };
  };
  window.parent.document.addEventListener("mousemove", window.parent.__lineMarkPointerTracker, true);
  window.parent.__lineMarkStageMove = (event) => {
    window.parent.__lineMarkLastPointer = { x: event.clientX, y: event.clientY };
    drawAt(event);
  };
  window.parent.document.addEventListener("mousemove", window.parent.__lineMarkStageMove, true);
  const redrawFromLastPointer = () => {
    const pointer = window.parent.__lineMarkLastPointer;
    if (!pointer || typeof pointer.x !== "number" || typeof pointer.y !== "number") return;
    drawAt({ clientX: pointer.x, clientY: pointer.y });
  };
  redrawFromLastPointer();
  [40, 120, 240, 420].forEach((delayMs) => {
    window.setTimeout(redrawFromLastPointer, delayMs);
  });
  const existingLoadHandlers = window.parent.__lineMarkZoomImageLoadHandlers;
  if (Array.isArray(existingLoadHandlers)) {
    existingLoadHandlers.forEach((item) => {
      try {
        item.image.removeEventListener("load", item.handler, true);
      } catch (error) {}
    });
  }
  window.parent.__lineMarkZoomImageLoadHandlers = [];
  const images = Array.from(window.parent.document.querySelectorAll('div[data-testid="stImage"] img'));
  images.forEach((imageNode) => {
    const handler = () => redrawFromLastPointer();
    imageNode.addEventListener("load", handler, true);
    window.parent.__lineMarkZoomImageLoadHandlers.push({ image: imageNode, handler });
  });
})();
</script>
