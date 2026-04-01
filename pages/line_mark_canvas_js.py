import json


def get_canvas_enhancement_script(hover_bridge_label: str = "", source_image_url: str = "") -> str:
    script = """
    <script>
    (function applyCanvasEnhancements() {
      const hoverBridgeLabel = __HOVER_BRIDGE_LABEL__;
      const sourceImageUrl = __SOURCE_IMAGE_URL__;
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
          const doc = frame.contentDocument || frame.contentWindow.document;
          if (!doc) return;
          if (!doc.getElementById(styleId)) {
            const style = doc.createElement("style");
            style.id = styleId;
            style.textContent = css;
            doc.head.appendChild(style);
          }
          doc.querySelectorAll("button, [role='button']").forEach((element) => {
            element.style.color = "#f3f4f6";
            element.style.opacity = "1";
          });
          doc.querySelectorAll("svg, svg *").forEach((element) => {
            element.style.stroke = "#f3f4f6";
            element.style.fill = "#f3f4f6";
            element.style.opacity = "1";
          });
          doc.querySelectorAll("img").forEach((element) => {
            element.style.filter = "invert(1) brightness(1.35) contrast(1.1)";
            element.style.opacity = "1";
          });

          const allCanvases = Array.from(doc.querySelectorAll("canvas"));
          const drawableCanvases = allCanvases.filter((canvas) => (canvas.width || 0) > 200 && (canvas.height || 0) > 200);
          const upperCanvas = doc.querySelector("canvas.upper-canvas") || drawableCanvases[0];
          const lowerCanvas = doc.querySelector("canvas.lower-canvas");
          // Run zoom logic only in the drawable-canvas iframe context.
          if (!upperCanvas || !lowerCanvas || (lowerCanvas.width || 0) < 200 || (lowerCanvas.height || 0) < 200) return;
          let lastBridgeValue = "";
          let lastBridgeAt = 0;

          const pushHoverToBridge = (mouse_x, mouse_y) => {
            if (!hoverBridgeLabel) return;
            const now = Date.now();
            if (now - lastBridgeAt < 80) return;
            const value = `${Math.round(mouse_x)},${Math.round(mouse_y)}`;
            if (value === lastBridgeValue) return;
            lastBridgeValue = value;
            lastBridgeAt = now;
            try {
              const parentDocument = window.parent.document;
              let bridgeInput = parentDocument.querySelector(`input[aria-label="${hoverBridgeLabel}"]`);
              if (!bridgeInput) {
                const labels = Array.from(parentDocument.querySelectorAll("label"));
                const matchingLabel = labels.find((labelNode) => (labelNode.textContent || "").trim() === hoverBridgeLabel);
                if (matchingLabel) {
                  const container = matchingLabel.closest('[data-testid="stTextInput"]');
                  if (container) bridgeInput = container.querySelector("input");
                }
              }
              if (!bridgeInput) return;
              const valueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value")?.set;
              if (valueSetter) {
                valueSetter.call(bridgeInput, value);
              } else {
                bridgeInput.value = value;
              }
              bridgeInput.dispatchEvent(new Event("input", { bubbles: true }));
              bridgeInput.dispatchEvent(new Event("change", { bubbles: true }));
              bridgeInput.dispatchEvent(new KeyboardEvent("keyup", { bubbles: true, key: "ArrowRight" }));
            } catch (error) {}
          };

          if (upperCanvas) {
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
            const zoom = 3;
            const radius = 30;
            let providedImage = null;
            if (sourceImageUrl) {
              providedImage = new Image();
              providedImage.src = sourceImageUrl;
            }
            let cachedBackgroundImage = null;
            let cachedBackgroundUrl = "";
            let lastSourceLabel = "NONE";

            const drawPanelLabel = (text) => {
              if (!sideContext) return;
              sideContext.fillStyle = "rgba(0, 0, 0, 0.65)";
              sideContext.fillRect(0, sidePanelCanvas.height - 20, sidePanelCanvas.width, 20);
              sideContext.fillStyle = "#00ffff";
              sideContext.font = "11px monospace";
              sideContext.fillText(text, 6, sidePanelCanvas.height - 6);
            };

            const getContainerBackgroundImage = () => {
              try {
                const candidates = [];
                let current = upperCanvas;
                for (let depth = 0; depth < 5 && current; depth += 1) {
                  candidates.push(current);
                  current = current.parentElement;
                }
                const matched = candidates.find((node) => {
                  const bg = window.getComputedStyle(node).backgroundImage || "";
                  return bg && bg !== "none";
                });
                if (!matched) return null;
                const backgroundImage = window.getComputedStyle(matched).backgroundImage || "";
                const match = backgroundImage.match(/^url\(["']?(.*?)["']?\)$/);
                if (!match || !match[1]) return null;
                const imageUrl = match[1];
                if (imageUrl !== cachedBackgroundUrl) {
                  cachedBackgroundUrl = imageUrl;
                  cachedBackgroundImage = new Image();
                  cachedBackgroundImage.src = imageUrl;
                }
                if (!cachedBackgroundImage || !cachedBackgroundImage.complete) return null;
                return { image: cachedBackgroundImage, rect: upperCanvas.getBoundingClientRect() };
              } catch (error) {
                return null;
              }
            };

            const getSourceTarget = () => {
              if (providedImage && providedImage.complete && (providedImage.naturalWidth || 0) > 0) {
                lastSourceLabel = "PROVIDED_IMG";
                return {
                  node: providedImage,
                  rect: upperCanvas.getBoundingClientRect(),
                  sourceWidth: providedImage.naturalWidth || upperCanvas.width || 0,
                  sourceHeight: providedImage.naturalHeight || upperCanvas.height || 0,
                  offsetX: 0,
                  offsetY: 0,
                };
              }
              try {
                const frameRect = frame.getBoundingClientRect();
                const parentImages = Array.from(window.parent.document.querySelectorAll("img")).filter((imageNode) => {
                  const width = imageNode.naturalWidth || imageNode.width || 0;
                  const height = imageNode.naturalHeight || imageNode.height || 0;
                  if (width < 300 || height < 300) return false;
                  const rect = imageNode.getBoundingClientRect();
                  const overlapsFrame =
                    rect.right > frameRect.left &&
                    rect.left < frameRect.right &&
                    rect.bottom > frameRect.top &&
                    rect.top < frameRect.bottom;
                  return overlapsFrame;
                });
                if (parentImages.length > 0) {
                  const bestImage = parentImages.reduce((largest, current) => {
                    const largestArea = (largest.naturalWidth || largest.width || 0) * (largest.naturalHeight || largest.height || 0);
                    const currentArea = (current.naturalWidth || current.width || 0) * (current.naturalHeight || current.height || 0);
                    return currentArea > largestArea ? current : largest;
                  });
                  lastSourceLabel = "PARENT_IMG";
                  return {
                    node: bestImage,
                    rect: bestImage.getBoundingClientRect(),
                    sourceWidth: bestImage.naturalWidth || bestImage.width || upperCanvas.width || 0,
                    sourceHeight: bestImage.naturalHeight || bestImage.height || upperCanvas.height || 0,
                    offsetX: 0,
                    offsetY: 0,
                    useGlobalCoords: true,
                  };
                }
              } catch (error) {}

              try {
                const fabricCanvas = upperCanvas.__canvas || lowerCanvas.__canvas;
                const fabricBackground = fabricCanvas && fabricCanvas.backgroundImage ? fabricCanvas.backgroundImage : null;
                const fabricElement =
                  fabricBackground && typeof fabricBackground.getElement === "function"
                    ? fabricBackground.getElement()
                    : (fabricBackground && (fabricBackground._element || fabricBackground.element)) || null;
                if (fabricElement) {
                  const scaleX = fabricBackground.scaleX || 1;
                  const scaleY = fabricBackground.scaleY || 1;
                  const left = fabricBackground.left || 0;
                  const top = fabricBackground.top || 0;
                  const canvasRect = lowerCanvas.getBoundingClientRect();
                  lastSourceLabel = "FABRIC_BG";
                  return {
                    node: fabricElement,
                    rect: canvasRect,
                    sourceWidth: (fabricElement.naturalWidth || fabricElement.width || lowerCanvas.width || 0) * scaleX,
                    sourceHeight: (fabricElement.naturalHeight || fabricElement.height || lowerCanvas.height || 0) * scaleY,
                    offsetX: left,
                    offsetY: top,
                  };
                }
              } catch (error) {}

              try {
                const docImages = Array.from(doc.querySelectorAll("img")).filter((imageNode) => {
                  const width = imageNode.naturalWidth || imageNode.width || 0;
                  const height = imageNode.naturalHeight || imageNode.height || 0;
                  return width >= 300 && height >= 300;
                });
                if (docImages.length > 0) {
                  const bestImage = docImages.reduce((largest, current) => {
                    const largestArea = (largest.naturalWidth || largest.width || 0) * (largest.naturalHeight || largest.height || 0);
                    const currentArea = (current.naturalWidth || current.width || 0) * (current.naturalHeight || current.height || 0);
                    return currentArea > largestArea ? current : largest;
                  });
                  lastSourceLabel = "IMG_DOC";
                  return {
                    node: bestImage,
                    rect: bestImage.getBoundingClientRect(),
                    sourceWidth: bestImage.naturalWidth || bestImage.width || upperCanvas.width || 0,
                    sourceHeight: bestImage.naturalHeight || bestImage.height || upperCanvas.height || 0,
                    offsetX: 0,
                    offsetY: 0,
                  };
                }
              } catch (error) {}

              const backgroundSource = getContainerBackgroundImage();
              if (backgroundSource && backgroundSource.image) {
                lastSourceLabel = "BG_IMG";
                return {
                  node: backgroundSource.image,
                  rect: backgroundSource.rect,
                  sourceWidth: backgroundSource.image.naturalWidth || upperCanvas.width || 0,
                  sourceHeight: backgroundSource.image.naturalHeight || upperCanvas.height || 0,
                  offsetX: 0,
                  offsetY: 0,
                };
              }
              if (lowerCanvas && (lowerCanvas.width || 0) > 0 && (lowerCanvas.height || 0) > 0) {
                lastSourceLabel = "LOWER_RAW";
                return {
                  node: lowerCanvas,
                  rect: lowerCanvas.getBoundingClientRect(),
                  sourceWidth: lowerCanvas.width || 0,
                  sourceHeight: lowerCanvas.height || 0,
                  offsetX: 0,
                  offsetY: 0,
                };
              }
              lastSourceLabel = "NONE";
              return null;
            };

            const updateZoomAt = (clientX, clientY) => {
              const sourceTarget = getSourceTarget();
              if (!lensContext || !sideContext) return;
              const targetRect = upperCanvas.getBoundingClientRect();
              const inside =
                clientX >= targetRect.left &&
                clientX <= targetRect.right &&
                clientY >= targetRect.top &&
                clientY <= targetRect.bottom;
              if (!inside) {
                lens.style.display = "none";
                return;
              }
              const x = clientX - targetRect.left;
              const y = clientY - targetRect.top;
              pushHoverToBridge(x, y);
              lens.style.left = `${clientX - radius}px`;
              lens.style.top = `${clientY - radius}px`;
              lens.style.display = "block";
              lensContext.clearRect(0, 0, lens.width, lens.height);
              sideContext.clearRect(0, 0, sidePanelCanvas.width, sidePanelCanvas.height);
              lensContext.save();
              lensContext.beginPath();
              lensContext.arc(radius, radius, radius - 1, 0, Math.PI * 2);
              lensContext.clip();
              const sample = (radius * 2) / zoom;
              try {
                if (!sourceTarget || !sourceTarget.node) throw new Error("uploaded image source not found");
                const sourceRect = sourceTarget.rect || sourceTarget.node.getBoundingClientRect();
                const sourceWidth = sourceTarget.sourceWidth || sourceTarget.node.width || sourceTarget.node.naturalWidth || targetRect.width;
                const sourceHeight = sourceTarget.sourceHeight || sourceTarget.node.height || sourceTarget.node.naturalHeight || targetRect.height;
                const scale_x = sourceWidth / Math.max(1, sourceRect.width);
                const scale_y = sourceHeight / Math.max(1, sourceRect.height);
                const offsetX = sourceTarget.offsetX || 0;
                const offsetY = sourceTarget.offsetY || 0;
                const frameRect = frame.getBoundingClientRect();
                const pointerClientX = sourceTarget.useGlobalCoords ? clientX + frameRect.left : clientX;
                const pointerClientY = sourceTarget.useGlobalCoords ? clientY + frameRect.top : clientY;
                const sample_x = (pointerClientX - sourceRect.left) * scale_x - offsetX;
                const sample_y = (pointerClientY - sourceRect.top) * scale_y - offsetY;
                const sample_w = Math.max(2, sample * scale_x);
                const sample_h = Math.max(2, sample * scale_y);
                const clamped_w = Math.min(sample_w, Math.max(2, sourceWidth - 1));
                const clamped_h = Math.min(sample_h, Math.max(2, sourceHeight - 1));
                const clamped_x = Math.max(0, Math.min(sample_x - clamped_w / 2, sourceWidth - clamped_w));
                const clamped_y = Math.max(0, Math.min(sample_y - clamped_h / 2, sourceHeight - clamped_h));
                lensContext.drawImage(sourceTarget.node, clamped_x, clamped_y, clamped_w, clamped_h, 0, 0, radius * 2, radius * 2);
                sideContext.imageSmoothingEnabled = false;
                sideContext.drawImage(
                  sourceTarget.node,
                  clamped_x,
                  clamped_y,
                  clamped_w,
                  clamped_h,
                  0,
                  0,
                  sidePanelCanvas.width,
                  sidePanelCanvas.height
                );
                sideContext.strokeStyle = "#00ffff";
                sideContext.lineWidth = 1;
                sideContext.beginPath();
                sideContext.moveTo(sidePanelCanvas.width / 2 - 10, sidePanelCanvas.height / 2);
                sideContext.lineTo(sidePanelCanvas.width / 2 + 10, sidePanelCanvas.height / 2);
                sideContext.moveTo(sidePanelCanvas.width / 2, sidePanelCanvas.height / 2 - 10);
                sideContext.lineTo(sidePanelCanvas.width / 2, sidePanelCanvas.height / 2 + 10);
                sideContext.stroke();
              } catch (error) {
                lensContext.fillStyle = "rgba(0,0,0,0.5)";
                lensContext.fillRect(0, 0, lens.width, lens.height);
                sideContext.fillStyle = "rgba(0,0,0,0.5)";
                sideContext.fillRect(0, 0, sidePanelCanvas.width, sidePanelCanvas.height);
                const errorText = (error && (error.name || error.message)) ? `${error.name || "ERR"}` : "ERR";
                drawPanelLabel(`SRC:${lastSourceLabel} ERR:${errorText}`);
              }
              lensContext.restore();
              lensContext.strokeStyle = "#00ffff";
              lensContext.lineWidth = 1;
              lensContext.beginPath();
              lensContext.arc(radius, radius, radius - 1, 0, Math.PI * 2);
              lensContext.stroke();
              if (sourceTarget && sourceTarget.node) {
                drawPanelLabel(`SRC:${lastSourceLabel} OK`);
              }
            };

            const previousMoveHandler = window.__lineMarkMoveHandler;
            const previousDownHandler = window.__lineMarkDownHandler;
            const previousUpHandler = window.__lineMarkUpHandler;
            if (previousMoveHandler) doc.removeEventListener("mousemove", previousMoveHandler, true);
            if (previousDownHandler) doc.removeEventListener("mousedown", previousDownHandler, true);
            if (previousUpHandler) doc.removeEventListener("mouseup", previousUpHandler, true);

            window.__lineMarkMoveHandler = (event) => updateZoomAt(event.clientX, event.clientY);
            window.__lineMarkDownHandler = (event) => updateZoomAt(event.clientX, event.clientY);
            window.__lineMarkUpHandler = (event) => updateZoomAt(event.clientX, event.clientY);

            doc.addEventListener("mousemove", window.__lineMarkMoveHandler, true);
            doc.addEventListener("mousedown", window.__lineMarkDownHandler, true);
            doc.addEventListener("mouseup", window.__lineMarkUpHandler, true);
          }
        } catch (error) {}
      });
      setTimeout(applyCanvasEnhancements, 1200);
    })();
    </script>
    """
    return (
        script.replace("__HOVER_BRIDGE_LABEL__", json.dumps(hover_bridge_label))
        .replace("__SOURCE_IMAGE_URL__", json.dumps(source_image_url))
    )
