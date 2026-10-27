(() => {
  'use strict';
  const body = document.body;
  body.classList.add('kw-report');
  const labels = { passed: '通过', failed: '失败', skipped: '跳过', error: '错误', xfailed: '预期失败', xpassed: '意外通过', rerun: '重跑', retried: '重试' };
  const mediaSelection = new Map();
  let mediaId = 0;
  let storedTheme;
  try { storedTheme = localStorage.getItem('kw-report-theme'); } catch (_) { /* file:// may disable storage. */ }
  function setTheme(theme) {
    body.dataset.theme = theme;
    document.documentElement.style.colorScheme = theme;
    document.querySelectorAll('[data-kw-theme]').forEach(button => {
      button.setAttribute('aria-pressed', String(button.dataset.kwTheme === theme));
    });
  }
  setTheme(['light', 'dark'].includes(storedTheme) ? storedTheme : 'light');

  function element(tag, className, text) {
    const node = document.createElement(tag);
    node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function selectMedia(artifacts, key) {
    artifacts.querySelectorAll('.kw-artifact-tab').forEach(tab => {
      tab.setAttribute('aria-selected', String(tab.dataset.media === key));
    });
    artifacts.querySelectorAll('.kw-artifact-panel').forEach(panel => {
      panel.hidden = panel.dataset.media !== key;
      if (panel.hidden) panel.querySelectorAll('video').forEach(video => video.pause());
    });
  }

  function enhanceRows() {
    document.querySelectorAll('#results-table tbody.results-table-row').forEach(row => {
      if (row.dataset.kwReady || !row.querySelector('.collapsible')) return;
      row.dataset.kwReady = 'true';
      const result = row.querySelector('.col-result');
      const status = Object.keys(labels).find(key => row.classList.contains(key));
      // Keep cells as direct click targets: pytest-html uses target.parentElement.dataset.id.
      if (result && status) result.textContent = labels[status];
      const detail = row.querySelector('td.extra');
      if (!detail) return;
      const log = detail.querySelector('.logwrapper');
      const extra = detail.querySelector('.extraHTML');
      const nativeMedia = detail.querySelector('.media');
      const artifacts = detail.querySelector('.kw-failure-artifacts');
      const hasExtras = Boolean(extra && extra.children.length);
      const hasNativeMedia = Boolean(nativeMedia && nativeMedia.style.display !== 'none');
      const needsMedia = hasExtras || hasNativeMedia || ['failed', 'error', 'xpassed'].includes(status);
      const layout = element('div', 'kw-detail-layout' + (needsMedia ? ' kw-has-media' : ''));
      const logPanel = element('section', 'kw-log-panel');
      logPanel.setAttribute('aria-label', '执行日志');
      const logHeading = element('div', 'kw-panel-heading');
      logHeading.append(element('strong', '', '执行日志'), element('small', '', 'Captured log / traceback'));
      logPanel.append(logHeading);
      if (log) {
        logPanel.append(log);
        const expander = log.querySelector('.logexpander');
        if (expander) { expander.setAttribute('role', 'button'); expander.setAttribute('tabindex', '0'); expander.setAttribute('aria-label', '展开或收起完整日志'); }
      }
      layout.append(logPanel);
      if (needsMedia) {
        const mediaPanel = element('section', 'kw-media-panel');
        mediaPanel.setAttribute('aria-label', '失败产物');
        const heading = element('div', 'kw-panel-heading');
        heading.append(element('strong', '', '失败产物'));
        detail.querySelectorAll('.kw-trace-button').forEach(link => heading.append(link));
        mediaPanel.append(heading);
        if (extra) mediaPanel.append(extra);
        if (nativeMedia) mediaPanel.append(nativeMedia);
        if (!hasExtras && !hasNativeMedia) mediaPanel.append(element('p', 'kw-media-empty', '当前用例未生成截图、录像或 Trace。'));
        layout.append(mediaPanel);
      } else {
        if (extra) logPanel.append(extra);
        if (nativeMedia) logPanel.append(nativeMedia);
      }
      // Preserve additional HTML supplied by other pytest-html hooks.
      [...detail.childNodes].forEach(node => logPanel.append(node));
      detail.append(layout);
      if (artifacts) {
        const tabs = [...artifacts.querySelectorAll('.kw-artifact-tab')];
        const unique = 'kw-media-' + (++mediaId);
        tabs.forEach((tab, index) => {
          tab.id = unique + '-tab-' + index;
          const panel = [...artifacts.querySelectorAll('.kw-artifact-panel')].find(item => item.dataset.media === tab.dataset.media);
          if (panel) {
            panel.id = unique + '-panel-' + index;
            tab.setAttribute('aria-controls', panel.id);
            panel.setAttribute('aria-labelledby', tab.id);
          }
        });
        const selected = mediaSelection.get(row.id);
        selectMedia(artifacts, tabs.some(tab => tab.dataset.media === selected) ? selected : tabs[0]?.dataset.media);
      }
    });
  }

  function initialise() {
    document.documentElement.lang = 'zh-CN';
    if (!document.querySelector('meta[name="viewport"]')) {
      const viewport = document.createElement('meta');
      viewport.name = 'viewport'; viewport.content = 'width=device-width, initial-scale=1';
      document.head.append(viewport);
    }
    const chrome = document.getElementById('kw-report-chrome');
    const top = chrome.querySelector('.kw-top');
    body.prepend(top);
    body.append(chrome.querySelector('.kw-footer'));
    chrome.remove();
    setTheme(body.dataset.theme);
    const title = document.getElementById('title');
    const generated = title.nextElementSibling;
    const heading = element('section', 'kw-heading');
    const main = element('div', 'kw-heading-main');
    title.before(heading);
    main.append(element('div', 'kw-eyebrow', 'EXECUTION REPORT'));
    const filename = title.textContent;
    title.textContent = '自动化测试报告';
    main.append(title);
    if (generated?.tagName === 'P') { generated.classList.add('kw-generated'); main.append(generated); }
    main.append(element('div', 'kw-team', '测试开发组：工具人1号 · ' + filename));
    heading.append(main);

    const environmentHeader = document.getElementById('environment-header');
    const environmentTable = document.getElementById('environment');
    const environment = element('section', 'kw-environment');
    environmentHeader.before(environment);
    environment.append(environmentHeader, environmentTable);
    environmentHeader.querySelector('h2').textContent = '运行环境';
    environmentHeader.classList.add('collapsed');
    environmentHeader.setAttribute('role', 'button');
    environmentHeader.setAttribute('tabindex', '0');
    environmentHeader.setAttribute('aria-controls', 'environment');
    environmentHeader.setAttribute('aria-expanded', 'false');
    environmentHeader.addEventListener('click', () => environmentHeader.setAttribute('aria-expanded', String(!environmentTable.classList.contains('hidden'))));
    environmentTable.classList.add('hidden');

    const summary = document.querySelector('.summary__data');
    summary.querySelector('h2').textContent = '执行汇总 / Summary';
    const controls = summary.querySelector('.controls');
    const counts = {};
    controls.querySelectorAll('input[data-test-result]').forEach(input => {
      const status = input.dataset.testResult;
      const span = input.nextElementSibling;
      const count = Number.parseInt(span.textContent, 10) || 0;
      counts[status] = count;
      span.textContent = count + ' ' + (labels[status] || status);
      const label = element('label', 'kw-filter-option');
      input.before(label); label.append(input, span);
    });
    const countMetadata = document.getElementById('kw-report-count');
    const rawData = JSON.parse(document.getElementById('data-container').dataset.jsonblob);
    const total = countMetadata ? Number(countMetadata.dataset.total) : Object.keys(rawData.tests).length;
    const statusSummary = element('div', 'kw-status-summary');
    ['passed', 'failed', 'skipped', 'error', 'xfailed', 'xpassed', 'rerun', 'retried'].forEach(key => {
      if (['passed', 'failed', 'skipped', 'error'].includes(key) || counts[key]) statusSummary.append(element('span', key, (counts[key] || 0) + ' ' + labels[key]));
    });
    const runCount = summary.querySelector('.run-count');
    const duration = runCount.textContent.match(/\btook (.+)\.$/);
    runCount.textContent = '共 ' + total + ' 个用例' + (duration ? ' · 总耗时 ' + duration[1] : ' · ' + runCount.textContent) + ' · 通过率 ' + (total ? ((counts.passed || 0) / total * 100).toFixed(1) : '0.0') + '%';
    runCount.after(statusSummary);
    const badge = element('span', 'kw-run-state' + (counts.failed || counts.error || counts.xpassed ? ' kw-state-failed' : ''));
    const running = summary.querySelector('.summary__reload__button:not(.hidden)');
    badge.textContent = running ? '执行中' : (counts.failed || counts.error || counts.xpassed ? '执行完成 · 存在失败用例' : '执行完成');
    heading.append(badge);

    const table = document.getElementById('results-table');
    const resultsHeading = element('div', 'kw-results-heading');
    resultsHeading.append(element('h2', '', '测试结果'));
    const collapse = controls.querySelector('.collapse');
    resultsHeading.append(collapse);
    // Remove the original slash separator while retaining the original buttons/listeners.
    [...collapse.childNodes].filter(node => node.nodeType === Node.TEXT_NODE).forEach(node => node.remove());
    collapse.querySelector('#show_all_details').textContent = '展开全部';
    collapse.querySelector('#hide_all_details').textContent = '收起全部';
    table.before(resultsHeading, controls);
    const filterHelp = summary.querySelector('p.filter');
    if (filterHelp) filterHelp.textContent = '勾选状态筛选测试结果';
    const tableWrap = element('div', 'kw-table-wrap');
    table.before(tableWrap); tableWrap.append(table);
    const headers = { result: '结果', testId: '测试用例 / Test', duration: '耗时' };
    table.querySelectorAll('th[data-column-type]').forEach(th => { if (headers[th.dataset.columnType]) th.textContent = headers[th.dataset.columnType]; });
    enhanceRows();
    // pytest-html replaces the table on every sort/filter/collapse; decorate each new row once.
    new MutationObserver(enhanceRows).observe(tableWrap, { childList: true, subtree: true });
  }

  document.addEventListener('click', event => {
    const theme = event.target.closest('[data-kw-theme]');
    if (theme) {
      setTheme(theme.dataset.kwTheme);
      try { localStorage.setItem('kw-report-theme', theme.dataset.kwTheme); } catch (_) { /* Optional preference storage. */ }
    }
    const tab = event.target.closest('.kw-artifact-tab');
    if (tab) {
      selectMedia(tab.closest('.kw-failure-artifacts'), tab.dataset.media);
      mediaSelection.set(tab.closest('tbody').id, tab.dataset.media);
    }
  });
  document.addEventListener('keydown', event => {
    const tab = event.target.closest('.kw-artifact-tab');
    if (tab && ['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) {
      const tabs = [...tab.parentElement.querySelectorAll('.kw-artifact-tab')];
      let index = tabs.indexOf(tab);
      if (event.key === 'Home') index = 0;
      else if (event.key === 'End') index = tabs.length - 1;
      else index = (index + (event.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length;
      event.preventDefault(); tabs[index].click(); tabs[index].focus();
    } else if (['Enter', ' '].includes(event.key) && event.target.matches('#environment-header, .logexpander')) {
      event.preventDefault(); event.target.click();
    }
  });
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initialise, { once: true });
  else initialise();
})();
