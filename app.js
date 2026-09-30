(() => {
  const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';

  const addHomeLine = document.querySelector('#add-home-line');
  const homeLines = document.querySelector('#home-lines');
  const lineTemplate = document.querySelector('#home-line-template');
  if (addHomeLine && homeLines && lineTemplate) {
    addHomeLine.addEventListener('click', () => {
      if (homeLines.children.length >= 12) return;
      homeLines.append(lineTemplate.content.cloneNode(true));
    });
    homeLines.addEventListener('click', (event) => {
      const button = event.target.closest('.remove-line');
      if (button && homeLines.children.length > 1) button.closest('.home-line').remove();
    });
  }

  const imageInput = document.querySelector('#outfit-image');
  const imageName = document.querySelector('#image-name');
  if (imageInput && imageName) {
    imageInput.addEventListener('change', () => {
      const file = imageInput.files?.[0];
      imageName.textContent = file ? `${file.name} · ${(file.size / 1024 / 1024).toFixed(1)} MB` : 'Images are sent to Gemini only when an API key is configured.';
    });
  }

  const form = document.querySelector('#planner-form');
  if (!form) return;

  const errorBox = document.querySelector('#form-error');
  const results = document.querySelector('#results');
  const submitButton = form.querySelector('button[type="submit"]');

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    errorBox.hidden = true;
    if (!form.reportValidity()) return;
    const planner = form.dataset.planner;
    const formData = new FormData(form);
    const budget = Number(formData.get('budget'));
    const currency = String(formData.get('currency'));
    let url = `/generate-${planner}`;
    let body;
    const headers = { 'X-CSRF-Token': csrfToken };

    if (planner === 'home') {
      const roomsByName = new Map();
      for (const row of homeLines.querySelectorAll('.home-line')) {
        const name = row.querySelector('.item-name').value.trim();
        if (!name) continue;
        const roomName = row.querySelector('.room-name').value;
        if (!roomsByName.has(roomName)) roomsByName.set(roomName, []);
        roomsByName.get(roomName).push({ name, quantity: Number(row.querySelector('.item-quantity').value) });
      }
      if (roomsByName.size === 0) {
        showError('Add at least one room item to build your plan.');
        return;
      }
      body = JSON.stringify({
        budget,
        currency,
        style: String(formData.get('style')),
        rooms: Array.from(roomsByName, ([room_type, items]) => ({ room_type, items })),
      });
      headers['Content-Type'] = 'application/json';
    } else if (planner === 'party') {
      body = JSON.stringify({
        budget,
        currency,
        event_type: String(formData.get('event_type')),
        guests: Number(formData.get('guests')),
        city: String(formData.get('city')).trim(),
        venue: String(formData.get('venue')),
        food_style: String(formData.get('food_style')),
      });
      headers['Content-Type'] = 'application/json';
    } else {
      body = formData;
    }

    submitButton.classList.add('is-loading');
    submitButton.disabled = true;
    try {
      const response = await fetch(url, { method: 'POST', headers, body, credentials: 'same-origin' });
      const data = await response.json();
      if (!response.ok) {
        const detail = Array.isArray(data.detail) ? data.detail.map((item) => item.msg).join(' ') : data.detail;
        throw new Error(detail || 'We could not create this plan. Check the details and try again.');
      }
      renderResults(data);
      results.hidden = false;
      results.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } catch (error) {
      showError(error.message || 'The service could not be reached. Please try again.');
    } finally {
      submitButton.classList.remove('is-loading');
      submitButton.disabled = false;
    }
  });

  function showError(message) {
    errorBox.textContent = message;
    errorBox.hidden = false;
    errorBox.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  function formatMoney(amount, currency) {
    try {
      return new Intl.NumberFormat(undefined, { style: 'currency', currency, maximumFractionDigits: 2 }).format(amount);
    } catch {
      return `${currency} ${Number(amount).toFixed(2)}`;
    }
  }

  function renderResults(data) {
    const currency = data.currency || 'USD';
    document.querySelector('#result-summary').textContent = data.summary;
    const source = document.querySelector('#result-source');
    source.textContent = data.source === 'gemini' ? 'GEMINI-ASSISTED' : 'LOCAL ESTIMATE';
    source.classList.toggle('is-fallback', data.source !== 'gemini');

    const allocations = document.querySelector('#result-allocations');
    allocations.replaceChildren();
    for (const allocation of data.allocations) {
      const item = document.createElement('div');
      item.className = 'allocation-item';
      const label = document.createElement('div');
      label.className = 'allocation-label';
      const category = document.createElement('b');
      category.textContent = allocation.category;
      const amount = document.createElement('span');
      amount.textContent = formatMoney(allocation.amount, currency);
      label.append(category, amount);
      const rationale = document.createElement('p');
      rationale.textContent = allocation.rationale;
      const meter = document.createElement('div');
      meter.className = 'allocation-meter';
      const bar = document.createElement('span');
      const share = data.budget > 0 ? Math.min(100, Math.max(0, allocation.amount / data.budget * 100)) : 0;
      bar.style.setProperty('--bar-width', `${share}%`);
      meter.append(bar);
      item.append(label, rationale, meter);
      allocations.append(item);
    }

    const recommendations = document.querySelector('#result-items');
    recommendations.replaceChildren();
    for (const suggestion of data.recommendations) {
      const card = document.createElement('article');
      card.className = 'recommendation-card';
      const top = document.createElement('div');
      top.className = 'rec-card-top';
      const category = document.createElement('span');
      category.textContent = suggestion.category;
      const price = document.createElement('b');
      const total = Number(suggestion.price) * Number(suggestion.quantity || 1);
      price.textContent = `${formatMoney(total, currency)}${suggestion.quantity > 1 ? ` · ${suggestion.quantity} items` : ''}`;
      top.append(category, price);
      const title = document.createElement('h3');
      title.textContent = suggestion.name;
      const reason = document.createElement('p');
      reason.textContent = suggestion.reason;
      const link = document.createElement('a');
      link.href = suggestion.url;
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      link.textContent = `Search ${suggestion.platform} ↗`;
      card.append(top, title, reason, link);
      recommendations.append(card);
    }

    const insights = document.querySelector('#result-insights');
    insights.replaceChildren();
    if (data.insights?.length) {
      const list = document.createElement('ul');
      for (const insight of data.insights) {
        const line = document.createElement('li');
        line.textContent = insight;
        list.append(line);
      }
      insights.append(list);
    }
    document.querySelector('#result-history-link').href = `/recommendations-details/${encodeURIComponent(data.id)}`;
  }
})();