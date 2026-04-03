import json


def get_canvas_enhancement_script(source_image_url: str = "", zoom_factor: int = 4) -> str:
    script = """
    <script>
    (function applyCanvasEnhancements() {
      const sourceImageUrl = __SOURCE_IMAGE_URL__;
      const zoomFactor = __ZOOM_FACTOR__;
      window.parent.__lineMarkZoomMode = "canvas";
      const styleId = "line-mark-crosshair-style";
      const css = `
        html, body, canvas, .upper-canvas, .lower-canvas { cursor: crosshair !important; }
        button, [role="button"] { color: #f3f4f6 !important; opacity: 1 !important; }
        svg, svg * { stroke: #f3f4f6 !important; fill: #f3f4f6 !important; opacity: 1 !important; }
        img { filter: invert(1) brightness(1.35) contrast(1.1) !important; opacity: 1 !important; }
      `;
      const frames = window.parent.document.querySelectorAll("iframe");
      frames.forEach((frame) => {
        try {
          if (window.parent.__lineMarkZoomMode !== "canvas") return;
          // Disable stage-image zoom while point-canvas zoom is active.
          const parentPanel = window.parent.document.getElementById("line-mark-side-zoom");
          if (parentPanel) parentPanel.remove();
          const stageMove = window.parent.__lineMarkStageMove;
          if (stageMove) {
            window.parent.document.removeEventListener("mousemove", stageMove, true);
            window.parent.__lineMarkStageMove = null;
          }

          const doc = frame.contentDocument || frame.contentWindow.document;
          if (!doc) return;
          if (!doc.getElementById(styleId)) {
            const style = doc.createElement("style");
            style.id = styleId;
            style.textContent = css;
            doc.head.appendChild(style);
          }

          const upperCanvas = doc.querySelector("canvas.upper-canvas");
          if (!upperCanvas) return;

          let lens = doc.getElementById("line-mark-lens");
          if (!lens) {
            lens = doc.createElement("canvas");
            lens.id = "line-mark-lens";
            lens.width = 60;
            lens.height = 60;
            lens.style.position = "fixed";
            lens.style.pointerEvents = "none";
            lens.style.zIndex = "2147483647";
            lens.style.border = "1px solid #00ffff";
            lens.style.borderRadius = "50%";
            lens.style.boxShadow = "0 0 0 1px rgba(0,0,0,0.7)";
            lens.style.display = "none";
            doc.body.appendChild(lens);
          }

          let sidePanel = doc.getElementById("line-mark-side-zoom");
          let sidePanelCanvas = doc.getElementById("line-mark-side-zoom-canvas");
          const staleStagePanel = window.parent.document.getElementById("line-mark-stage-image-zoom");
          if (staleStagePanel) {
            staleStagePanel.remove();
          }
          if (!sidePanel || !sidePanelCanvas) {
            sidePanel = doc.createElement("div");
            sidePanel.id = "line-mark-side-zoom";
            sidePanel.style.position = "fixed";
            sidePanel.style.right = "12px";
            sidePanel.style.top = "12px";
            sidePanel.style.width = "170px";
            sidePanel.style.height = "170px";
            sidePanel.style.border = "1px solid #00ffff";
            sidePanel.style.background = "rgba(0,0,0,0.72)";
            sidePanel.style.borderRadius = "8px";
            sidePanel.style.zIndex = "2147483647";
            sidePanel.style.pointerEvents = "none";
            sidePanel.style.display = "none";
            sidePanelCanvas = doc.createElement("canvas");
            sidePanelCanvas.id = "line-mark-side-zoom-canvas";
            sidePanelCanvas.width = 168;
            sidePanelCanvas.height = 168;
            sidePanelCanvas.style.width = "168px";
            sidePanelCanvas.style.height = "168px";
            sidePanelCanvas.style.display = "block";
            sidePanel.appendChild(sidePanelCanvas);
            doc.body.appendChild(sidePanel);
          }

          const lensContext = lens.getContext("2d");
          const sideContext = sidePanelCanvas.getContext("2d");
          if (!lensContext || !sideContext || !sourceImageUrl) return;

          const providedImage = new Image();
          providedImage.src = sourceImageUrl;
          providedImage.onload = () => {
            const zoom = zoomFactor;
            const radius = 30;
            const prevMove = window.__lineMarkMoveHandler;
            const prevDown = window.__lineMarkDownHandler;
            const prevUp = window.__lineMarkUpHandler;
            if (prevMove) doc.removeEventListener("mousemove", prevMove, true);
            if (prevDown) doc.removeEventListener("mousedown", prevDown, true);
            if (prevUp) doc.removeEventListener("mouseup", prevUp, true);

            const drawAt = (clientX, clientY) => {
              const targetRect = upperCanvas.getBoundingClientRect();
              sidePanel.style.left = `${Math.round(targetRect.right + 12)}px`;
              sidePanel.style.top = `${Math.round(targetRect.top)}px`;
              sidePanel.style.right = "auto";
              const inside =
                clientX >= targetRect.left &&
                clientX <= targetRect.right &&
                clientY >= targetRect.top &&
                clientY <= targetRect.bottom;
              if (!inside) {
                lens.style.display = "none";
                sidePanel.style.display = "none";
                return;
              }

              const sxScale = providedImage.naturalWidth / Math.max(1, targetRect.width);
              const syScale = providedImage.naturalHeight / Math.max(1, targetRect.height);
              const sample = (radius * 2) / zoom;
              const sampleX = (clientX - targetRect.left) * sxScale;
              const sampleY = (clientY - targetRect.top) * syScale;
              const sampleW = Math.max(2, sample * sxScale);
              const sampleH = Math.max(2, sample * syScale);
              const srcX = sampleX - sampleW / 2;
              const srcY = sampleY - sampleH / 2;
              const srcX0 = Math.max(0, srcX);
              const srcY0 = Math.max(0, srcY);
              const srcX1 = Math.min(providedImage.naturalWidth, srcX + sampleW);
              const srcY1 = Math.min(providedImage.naturalHeight, srcY + sampleH);
              const srcW = Math.max(0, srcX1 - srcX0);
              const srcH = Math.max(0, srcY1 - srcY0);
              const destLensSize = radius * 2;
              const dstX = (Math.max(0, srcX0 - srcX) / sampleW) * destLensSize;
              const dstY = (Math.max(0, srcY0 - srcY) / sampleH) * destLensSize;
              const dstW = (srcW / sampleW) * destLensSize;
              const dstH = (srcH / sampleH) * destLensSize;

              lens.style.left = `${clientX - radius}px`;
              lens.style.top = `${clientY - radius}px`;
              lens.style.display = "block";
              sidePanel.style.display = "block";

              lensContext.clearRect(0, 0, lens.width, lens.height);
              lensContext.fillStyle = "rgba(0,0,0,0.55)";
              lensContext.fillRect(0, 0, lens.width, lens.height);
              lensContext.save();
              lensContext.beginPath();
              lensContext.arc(radius, radius, radius - 1, 0, Math.PI * 2);
              lensContext.clip();
              lensContext.imageSmoothingEnabled = false;
              if (srcW > 0 && srcH > 0 && dstW > 0 && dstH > 0) {
                lensContext.drawImage(providedImage, srcX0, srcY0, srcW, srcH, dstX, dstY, dstW, dstH);
              }
              lensContext.restore();
              lensContext.strokeStyle = "#00ffff";
              lensContext.lineWidth = 1;
              lensContext.beginPath();
              lensContext.arc(radius, radius, radius - 1, 0, Math.PI * 2);
              lensContext.stroke();

              sideContext.clearRect(0, 0, sidePanelCanvas.width, sidePanelCanvas.height);
              sideContext.fillStyle = "rgba(0,0,0,0.55)";
              sideContext.fillRect(0, 0, sidePanelCanvas.width, sidePanelCanvas.height);
              sideContext.imageSmoothingEnabled = false;
              if (srcW > 0 && srcH > 0) {
                sideContext.drawImage(
                  providedImage,
                  srcX0,
                  srcY0,
                  srcW,
                  srcH,
                  (Math.max(0, srcX0 - srcX) / sampleW) * sidePanelCanvas.width,
                  (Math.max(0, srcY0 - srcY) / sampleH) * sidePanelCanvas.height,
                  (srcW / sampleW) * sidePanelCanvas.width,
                  (srcH / sampleH) * sidePanelCanvas.height
                );
              }
              sideContext.strokeStyle = "#00ffff";
              sideContext.lineWidth = 1.25;
              sideContext.lineCap = "round";
              sideContext.lineJoin = "round";
              sideContext.beginPath();
              sideContext.moveTo(sidePanelCanvas.width / 2 - 10, sidePanelCanvas.height / 2);
              sideContext.lineTo(sidePanelCanvas.width / 2 + 10, sidePanelCanvas.height / 2);
              sideContext.moveTo(sidePanelCanvas.width / 2, sidePanelCanvas.height / 2 - 10);
              sideContext.lineTo(sidePanelCanvas.width / 2, sidePanelCanvas.height / 2 + 10);
              sideContext.stroke();
            };

            window.__lineMarkMoveHandler = (event) => drawAt(event.clientX, event.clientY);
            window.__lineMarkDownHandler = (event) => drawAt(event.clientX, event.clientY);
            window.__lineMarkUpHandler = (event) => drawAt(event.clientX, event.clientY);
            doc.addEventListener("mousemove", window.__lineMarkMoveHandler, true);
            doc.addEventListener("mousedown", window.__lineMarkDownHandler, true);
            doc.addEventListener("mouseup", window.__lineMarkUpHandler, true);
          };
        } catch (error) {}
      });
      setTimeout(applyCanvasEnhancements, 1200);
    })();
    </script>
    """
    return (
        script.replace("__SOURCE_IMAGE_URL__", json.dumps(source_image_url))
        .replace("__ZOOM_FACTOR__", str(int(zoom_factor)))
    )


def get_stage_image_zoom_script(zoom_factor: int = 7) -> str:
    return """
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
        ctx.lineWidth = 1.25;
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
      window.parent.__lineMarkStageMove = drawAt;
      window.parent.document.addEventListener("mousemove", drawAt, true);
    })();
    </script>
    """.replace("__ZOOM_FACTOR__", str(int(zoom_factor)))


def get_stage_hover_swap_script(thin_image_url: str, thick_image_url: str) -> str:
    script = """
    <script>
    (function applyStageHoverSwap() {
      const thinUrl = __THIN_IMAGE_URL__;
      const thickUrl = __THICK_IMAGE_URL__;
      if (!thinUrl || !thickUrl) return;
      const images = Array.from(window.parent.document.querySelectorAll('div[data-testid="stImage"] img'));
      if (!images.length) return;
      const target = images[0];
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
        const pointer = window.parent.__lineMarkLastPointer;
        if (pointer && isInsideTarget(pointer.x, pointer.y)) {
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
    """
    return (
        script.replace("__THIN_IMAGE_URL__", json.dumps(thin_image_url))
        .replace("__THICK_IMAGE_URL__", json.dumps(thick_image_url))
    )
