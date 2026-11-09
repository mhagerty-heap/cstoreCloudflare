/* ShopExpress - Main JS */

document.addEventListener('DOMContentLoaded', function () {

  // ── Cart Count Badge Updater ───────────────────────────────
  function updateCartBadge(count) {
    const badge = document.getElementById('cart-count');
    if (badge) {
      badge.textContent = count;
      badge.classList.toggle('d-none', count === 0);
    }
  }

  // ── Toast Notification ────────────────────────────────────
  function showToast(message, type = 'success') {
    const container = document.createElement('div');
    container.style.cssText = 'position:fixed;bottom:20px;right:20px;z-index:9999;';
    container.innerHTML = `
      <div class="toast align-items-center text-bg-${type} border-0 show shadow-lg" role="alert" style="min-width:280px;">
        <div class="d-flex">
          <div class="toast-body fw-semibold">
            <i class="bi bi-${type === 'success' ? 'check-circle' : 'exclamation-circle'} me-2"></i>${message}
          </div>
          <button type="button" class="btn-close btn-close-white me-2 m-auto" onclick="this.closest('[style]').remove()"></button>
        </div>
      </div>`;
    document.body.appendChild(container);
    setTimeout(() => container.remove(), 3500);
  }

  // ── Add to Cart (static demo: just go to the cart) ───────
  document.querySelectorAll('.btn-add-to-cart-ajax').forEach(btn => {
    btn.addEventListener('click', function (e) {
      e.preventDefault();
      window.location.href = '/cart';
    });
  });

  // ── Quantity Stepper ──────────────────────────────────────
  document.querySelectorAll('.qty-btn, .qty-btn-action').forEach(btn => {
    btn.addEventListener('click', function () {
      const input = this.closest('.qty-group').querySelector('.qty-input');
      if (!input) return;
      let val = parseInt(input.value) || 1;
      const min = parseInt(input.min) || 1;
      const max = parseInt(input.max) || 9999;
      if (this.dataset.action === 'increase') val = Math.min(val + 1, max);
      if (this.dataset.action === 'decrease') val = Math.max(val - 1, min);
      input.value = val;
    });
  });

  // ── Variant Selector ──────────────────────────────────────
  const variantOptions = document.querySelectorAll('.variant-option, .attr-btn');
  const selectedVariantInput = document.getElementById('selected-variant');
  const priceDisplay = document.getElementById('product-price');

  variantOptions.forEach(opt => {
    opt.addEventListener('click', function () {
      variantOptions.forEach(o => o.classList.remove('active'));
      this.classList.add('active');

      if (selectedVariantInput) selectedVariantInput.value = this.dataset.variantId;

      if (this.dataset.price && priceDisplay) {
        priceDisplay.textContent = '$' + parseFloat(this.dataset.price).toFixed(2);
      }
    });
  });

  // ── Image Gallery ─────────────────────────────────────────
  document.querySelectorAll('.thumbnail-img').forEach(thumb => {
    thumb.addEventListener('click', function () {
      const mainImg = document.getElementById('mainImage');
      if (mainImg) mainImg.src = this.src;
      document.querySelectorAll('.thumbnail-img').forEach(t => t.classList.remove('border-primary'));
      this.classList.add('border-primary');
    });
  });

  // ── Auto-dismiss alerts ───────────────────────────────────
  document.querySelectorAll('.alert.alert-dismissible').forEach(alert => {
    setTimeout(() => {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
      if (bsAlert) bsAlert.close();
    }, 5000);
  });

  // ── Admin: Confirm Delete ─────────────────────────────────
  document.querySelectorAll('[data-confirm]').forEach(el => {
    el.addEventListener('click', function (e) {
      if (!confirm(this.dataset.confirm || 'Are you sure?')) e.preventDefault();
    });
  });

});

// ── Static demo: there is no backend, so forms only navigate ─────────────
document.addEventListener('submit', function (e) {
  var action = e.target.getAttribute('action') || '';
  e.preventDefault();
  if (action === '/cart/add') window.location.href = '/cart';
  else if (action === '/checkout') window.location.href = '/checkout/confirmation/ORD-1794240459025';
});

function staticCouponNotice(id) {
  var el = document.getElementById(id);
  if (el) el.innerHTML = '<span class="text-muted">Coupons are not available in this demo.</span>';
}
window.applyCoupon = function () { staticCouponNotice('couponMsg'); };
window.applyCheckoutCoupon = function () { staticCouponNotice('checkoutCouponMsg'); };
window.removeCheckoutCoupon = function () {};
