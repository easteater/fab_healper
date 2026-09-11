window.__fab = window.__fab || {};

// 步骤A:点击第一个"未购买"的商品卡(含"已保存在我的库中"的跳过)
window.__fab.clickFirstUnpurchased = () => {
  const cards = document.querySelectorAll('[class*="fabkit-Surface-root"]');
  for (const card of cards) {
    if ((card.textContent || '').includes('已保存在我的库中')) continue;
    const link = card.querySelector('a[href*="/listings/"]');
    if (link) {
      link.click();
      return { ok: true, href: link.getAttribute('href') };
    }
  }
  return { ok: false, reason: 'no unpurchased card' };
};

// 步骤B:在商品页点下单按钮,自动识别两种页面类型。完成入库后通过 isComplete 检测
window.__fab.buyNow = async () => {
  const buttons = Array.from(document.querySelectorAll('button'));
  // 半收费页:有"添加至购物车" + 许可下拉 -> 先选免费档,再添加到我的库
  const cartBtn = buttons.find((b) => {
    const label = b.querySelector('.fabkit-Button-label');
    return label && (label.textContent || '').includes('添加至购物车');
  });
  if (cartBtn && window.__fab.selectFreeLicense) {
    const sel = await window.__fab.selectFreeLicense();
    const add = window.__fab.addToLibrary ? await window.__fab.addToLibrary() : {};
    const complete = window.__fab.isComplete ? window.__fab.isComplete() : false;
    return {
      ok: true,
      type: '半收费(有许可)',
      action: '添加到我的库',
      license: sel,
      add: add,
      complete,
    };
  }
  // 纯免费页:直接添加到我的库
  if (window.__fab.addToLibrary) {
    const add = await window.__fab.addToLibrary();
    const complete = window.__fab.isComplete ? window.__fab.isComplete() : false;
    return { ok: true, type: '纯免费', action: add.action, complete };
  }
  // 兜底:立即购买
  const buyBtn = buttons.find((b) => (b.textContent || '').includes('立即购买'));
  if (buyBtn) {
    buyBtn.click();
    return { ok: true, type: '半收费(有许可)', action: '立即购买' };
  }
  const titles = Array.from(document.querySelectorAll('h2')).map((h) => h.textContent).join(' | ');
  return { ok: false, reason: 'no action button found', titles: titles };
};
