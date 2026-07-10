(function () {
  const CSRF_TOKEN = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';

  function statusEl(row) {
    return row.querySelector('.row-status');
  }

  function setStatus(row, state, text) {
    const el = statusEl(row);
    el.dataset.status = state;
    el.querySelector('.status-text').textContent = text;
    const retry = el.querySelector('.retry-button');
    retry.hidden = state !== 'failed';
    row.classList.remove('saving', 'saved', 'failed', 'conflict');
    row.classList.add(state);
  }

  function formatError(payload) {
    if (!payload) return '保存失败';
    if (typeof payload.error === 'string') return payload.error;
    if (payload.errors && typeof payload.errors === 'object') {
      const messages = [];
      Object.values(payload.errors).forEach((value) => {
        if (Array.isArray(value)) messages.push(...value);
        else messages.push(String(value));
      });
      return messages.length ? messages.join('；') : '保存失败';
    }
    return '保存失败';
  }

  function rowData(row) {
    return {
      assessmentId: row.dataset.assessmentId,
      version: parseInt(row.dataset.version, 10),
      current_level: row.querySelector('.field-current-level').value,
      target_level: row.querySelector('.field-target-level').value,
      priority: row.querySelector('.field-priority').value,
      included: row.querySelector('.field-included').checked,
      planned_quarter: row.querySelector('.field-quarter').value,
      planned_month: row.querySelector('.field-month').value,
    };
  }

  function updateRowData(row, values) {
    if (values && 'gap' in values) row.dataset.gap = values.gap ?? '';
    if (values && 'priority' in values) row.dataset.priority = values.priority ?? '';
    if (values && 'included' in values) row.dataset.included = values.included ? '1' : '0';
    const current = row.querySelector('.field-current-level').value;
    const target = row.querySelector('.field-target-level').value;
    row.dataset.filled = (current !== '' && target !== '') ? '1' : '0';
    populateFilterOptions();
  }

  async function saveRow(row) {
    const data = rowData(row);
    setStatus(row, 'saving', '保存中…');

    try {
      const response = await fetch(`/learning/assessment/${data.assessmentId}/save/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': CSRF_TOKEN,
        },
        body: JSON.stringify(data),
      });

      if (response.status === 409) {
        const payload = await response.json().catch(() => ({}));
        if (payload.error === 'conflict') {
          setStatus(row, 'conflict', '数据已过期，请刷新页面');
          row.dataset.version = payload.version;
          return;
        }
        if (payload.error === 'archived') {
          setStatus(row, 'conflict', '周期已归档');
          return;
        }
      }

      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        setStatus(row, 'failed', formatError(payload));
        return;
      }

      const payload = await response.json();
      row.dataset.version = payload.version;
      row.querySelector('.field-gap').textContent = payload.values.gap ?? '-';
      updateRowData(row, payload.values);
      updateCounters(payload.counts);
      setStatus(row, 'saved', '已保存');
    } catch (err) {
      setStatus(row, 'failed', '网络错误');
    }
  }

  function updateCounters(counts) {
    if (!counts) return;
    const assessed = document.getElementById('assessed-count');
    const total = document.getElementById('total-count');
    const included = document.getElementById('included-count');
    if (assessed) assessed.textContent = counts.assessed;
    if (total) total.textContent = counts.total;
    if (included) included.textContent = counts.included;
  }

  function attachRowListeners(row) {
    const inputs = row.querySelectorAll(
      '.field-current-level, .field-target-level, .field-priority, .field-included, .field-quarter, .field-month'
    );
    inputs.forEach((input) => {
      input.addEventListener('change', () => {
        row.dataset.unsaved = '1';
        saveRow(row);
      });
    });

    const retry = row.querySelector('.retry-button');
    retry?.addEventListener('click', () => saveRow(row));
  }

  function visibleCapabilityRows() {
    return Array.from(document.querySelectorAll('.capability-row')).filter(
      (row) => row.offsetParent !== null
    );
  }

  function moveFocus(row, inputClass, direction) {
    const rows = visibleCapabilityRows();
    const index = rows.indexOf(row);
    const next = rows[index + direction];
    if (!next) return;
    const input = next.querySelector('.' + inputClass);
    if (input) input.focus();
  }

  document.querySelectorAll('.capability-row').forEach(attachRowListeners);

  document.querySelectorAll('.capability-row').forEach((row) => {
    row.addEventListener('keydown', (e) => {
      const input = e.target;
      if (!input.matches('select, input')) return;
      const classList = Array.from(input.classList);
      const fieldClass = classList.find((c) => c.startsWith('field-'));
      if (!fieldClass) return;
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        moveFocus(row, fieldClass, 1);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        moveFocus(row, fieldClass, -1);
      }
    });
  });

  document.getElementById('select-all')?.addEventListener('change', (e) => {
    document.querySelectorAll('.capability-row').forEach((row) => {
      if (row.offsetParent !== null) {
        row.querySelector('.row-select').checked = e.target.checked;
      }
    });
  });

  document.getElementById('batch-apply')?.addEventListener('click', async () => {
    const ids = Array.from(document.querySelectorAll('.capability-row .row-select:checked'))
      .map((cb) => cb.closest('.capability-row').dataset.assessmentId);
    if (ids.length === 0) return;

    const payload = { ids };
    const included = document.getElementById('batch-included');
    const priority = document.getElementById('batch-priority');
    const quarter = document.getElementById('batch-quarter');
    const month = document.getElementById('batch-month');

    if (included.checked) payload.included = true;
    if (priority.value) payload.priority = priority.value;
    if (quarter.value) payload.planned_quarter = quarter.value;
    if (month.value) payload.planned_month = month.value + '-01';

    try {
      const response = await fetch('/learning/assessment/batch/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': CSRF_TOKEN,
        },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        alert('批量更新失败');
        return;
      }
      const result = await response.json();
      updateCounters(result.counts);
      window.location.reload();
    } catch (err) {
      alert('批量更新失败');
    }
  });

  function fillSelect(id, values) {
    const select = document.getElementById(id);
    if (!select) return;
    const current = select.value;
    const existing = new Set();
    for (let i = 0; i < select.options.length; i++) {
      existing.add(select.options[i].value);
    }
    Array.from(values)
      .filter((v) => v)
      .sort()
      .forEach((value) => {
        if (!existing.has(value)) {
          const option = document.createElement('option');
          option.value = value;
          option.textContent = value;
          select.appendChild(option);
        }
      });
    if (existing.has(current)) select.value = current;
  }

  function populateFilterOptions() {
    const rows = document.querySelectorAll('.capability-row');
    const categories = new Set();
    const l1 = new Set();
    const l2 = new Set();
    const levels = new Set();
    rows.forEach((row) => {
      categories.add(row.dataset.category);
      l1.add(row.dataset.domainL1);
      l2.add(row.dataset.domainL2);
      if (row.dataset.suggestedLevel) levels.add(row.dataset.suggestedLevel);
    });
    fillSelect('filter-category', categories);
    fillSelect('filter-domain-l1', l1);
    fillSelect('filter-domain-l2', l2);
    fillSelect('filter-suggested-level', levels);
  }

  function matchesFilters(row) {
    const category = document.getElementById('filter-category')?.value;
    const domainL1 = document.getElementById('filter-domain-l1')?.value;
    const domainL2 = document.getElementById('filter-domain-l2')?.value;
    const suggested = document.getElementById('filter-suggested-level')?.value;
    const gap = document.getElementById('filter-gap')?.value;
    const priority = document.getElementById('filter-priority')?.value;
    const included = document.getElementById('filter-included')?.value;
    const filled = document.getElementById('filter-filled')?.value;

    if (category && row.dataset.category !== category) return false;
    if (domainL1 && row.dataset.domainL1 !== domainL1) return false;
    if (domainL2 && row.dataset.domainL2 !== domainL2) return false;
    if (suggested && row.dataset.suggestedLevel !== suggested) return false;

    if (gap) {
      const gapValue = row.dataset.gap === '' ? null : parseInt(row.dataset.gap, 10);
      if (gap === '0' && gapValue !== 0) return false;
      if (gap === '1-2' && (gapValue === null || gapValue < 1 || gapValue > 2)) return false;
      if (gap === '3+' && (gapValue === null || gapValue < 3)) return false;
    }

    if (priority && row.dataset.priority !== priority) return false;
    if (included && row.dataset.included !== included) return false;
    if (filled && row.dataset.filled !== filled) return false;

    return true;
  }

  function applyFilters() {
    document.querySelectorAll('.capability-row').forEach((row) => {
      row.style.display = matchesFilters(row) ? '' : 'none';
    });
  }

  document
    .querySelectorAll(
      '#filter-category, #filter-domain-l1, #filter-domain-l2, #filter-suggested-level, #filter-gap, #filter-priority, #filter-included, #filter-filled'
    )
    .forEach((select) => select.addEventListener('change', applyFilters));

  populateFilterOptions();
})();
