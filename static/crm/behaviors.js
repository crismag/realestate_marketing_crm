/* CRM behaviours for CrisGen Drawer, Modal and Tabs.
   Contract: CrisGen UI 1.1 vanilla (data-cg, data-cg-part, data-cg-on-click, data-state)
   at development_design_systems commit e1c1a4f1e98ecc4dec9ae4eb16fa646069e94278.
   This file is CRM code. It does not copy targets/vanilla/behaviors.mjs, because that
   runtime writes inline styles and this app's Content-Security-Policy forbids them.
   The tab indicator is therefore not slid; selected tabs are styled in crm.css. */
(function () {
  "use strict";

  var pending = document.getElementById("behaviors-note");
  if (pending) pending.setAttribute("hidden", "");

  var OVERLAY = "[data-cg='drawer'], [data-cg='modal']";

  function parseCall(value) {
    try {
      var spec = JSON.parse(value);
      if (!spec || typeof spec.call !== "string" || !Array.isArray(spec.args)) return null;
      return spec;
    } catch (err) {
      return null;
    }
  }

  function focusable(root) {
    return Array.prototype.filter.call(
      root.querySelectorAll("a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled])"),
      function (el) {
        return el.getClientRects().length > 0 && window.getComputedStyle(el).visibility !== "hidden";
      }
    );
  }

  function takeFocus(root) {
    var items = focusable(root);
    for (var i = 0; i < items.length; i++) {
      items[i].focus();
      if (root.contains(document.activeElement)) return true;
    }
    return false;
  }

  function openOverlays() {
    return Array.prototype.slice.call(document.querySelectorAll("[data-cg='drawer'][data-state='open'], [data-cg='modal'][data-state='open']"));
  }

  function closeOverlay(el, restore) {
    if (!el || el.getAttribute("data-state") === "closed") return;
    el.setAttribute("data-state", "closed");
    el.setAttribute("aria-hidden", "true");
    el.setAttribute("inert", "");
    if (restore && el._returnFocus && typeof el._returnFocus.focus === "function") {
      el._returnFocus.focus();
    }
  }

  function openOverlay(el) {
    if (!el) return;
    openOverlays().forEach(function (other) {
      if (other !== el) closeOverlay(other, false);
    });
    el._returnFocus = document.activeElement;
    el.setAttribute("data-state", "open");
    el.removeAttribute("aria-hidden");
    el.removeAttribute("inert");
    if (!takeFocus(el)) {
      window.requestAnimationFrame(function () {
        if (el.getAttribute("data-state") === "open") takeFocus(el);
      });
    }
  }

  function toggleOverlay(el) {
    if (!el) return;
    if (el.getAttribute("data-state") === "open") closeOverlay(el, true);
    else openOverlay(el);
  }

  function dispatch(spec) {
    var name = spec.call;
    var id = spec.args[0];
    var el = typeof id === "string" ? document.getElementById(id) : null;
    if (name === "drawer.open" || name === "modal.open") openOverlay(el);
    else if (name === "drawer.toggle" || name === "modal.toggle" || name === "drawer.close" || name === "modal.close") {
      if (name.endsWith(".close")) closeOverlay(el, true);
      else toggleOverlay(el);
    }
  }

  function activateTab(tab) {
    var root = tab.closest("[data-cg='tabs']");
    if (!root) return;
    var panelId = tab.getAttribute("aria-controls");
    Array.prototype.forEach.call(root.querySelectorAll("[data-cg-part='tab']"), function (item) {
      var on = item === tab;
      item.setAttribute("aria-selected", on ? "true" : "false");
      item.tabIndex = on ? 0 : -1;
    });
    Array.prototype.forEach.call(root.querySelectorAll(".cg-tabs__panel"), function (panel) {
      panel.setAttribute("data-state", panel.id === panelId ? "active" : "inactive");
    });
    var view = tab.getAttribute("data-view");
    if (view) {
      var url = new URL(window.location.href);
      url.searchParams.set("view", view);
      window.history.replaceState(null, "", url);
      Array.prototype.forEach.call(document.querySelectorAll("input[name='view']"), function (input) {
        input.value = view;
      });
    }
  }

  document.addEventListener("click", function (event) {
    var tab = event.target.closest("[data-cg='tabs'] [data-cg-part='tab']");
    if (tab) {
      event.preventDefault();
      activateTab(tab);
      return;
    }
    var trigger = event.target.closest("[data-cg-on-click]");
    if (trigger) {
      var spec = parseCall(trigger.getAttribute("data-cg-on-click"));
      if (spec) {
        event.preventDefault();
        dispatch(spec);
      }
      return;
    }
    var close = event.target.closest("[data-cg-part='close']");
    if (close) {
      var parent = close.closest(OVERLAY);
      if (parent) {
        event.preventDefault();
        closeOverlay(parent, true);
      }
      return;
    }
    var overlay = event.target.closest(OVERLAY);
    if (overlay && event.target === overlay) closeOverlay(overlay, true);
  });

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") {
      var open = openOverlays();
      if (open.length) {
        event.preventDefault();
        closeOverlay(open[open.length - 1], true);
      }
      return;
    }
    var tab = event.target.closest && event.target.closest("[data-cg-part='tab']");
    if (tab && (event.key === "ArrowLeft" || event.key === "ArrowRight" || event.key === "ArrowUp" || event.key === "ArrowDown" || event.key === "Home" || event.key === "End")) {
      var root = tab.closest("[data-cg='tabs']");
      var tabs = Array.prototype.slice.call(root.querySelectorAll("[data-cg-part='tab']"));
      var index = tabs.indexOf(tab);
      var vertical = root.getAttribute("data-orientation") === "vertical";
      var nextKey = vertical ? "ArrowDown" : "ArrowRight";
      var prevKey = vertical ? "ArrowUp" : "ArrowLeft";
      var target = index;
      if (event.key === nextKey) target = (index + 1) % tabs.length;
      else if (event.key === prevKey) target = (index - 1 + tabs.length) % tabs.length;
      else if (event.key === "Home") target = 0;
      else if (event.key === "End") target = tabs.length - 1;
      else return;
      event.preventDefault();
      activateTab(tabs[target]);
      tabs[target].focus();
      return;
    }
    if (event.key !== "Tab") return;
    var overlays = openOverlays();
    var current = overlays[overlays.length - 1];
    if (!current || !current.contains(document.activeElement)) return;
    var items = focusable(current);
    if (!items.length) {
      event.preventDefault();
      return;
    }
    var first = items[0];
    var last = items[items.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  });
})();
