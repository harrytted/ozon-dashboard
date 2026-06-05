const test = require('node:test');
const assert = require('node:assert/strict');
const ops = require('../frontend/app.js');

test('platform options only include Ozon for store binding', () => {
  assert.deepEqual(ops.getPlatformOptions(), ['Ozon']);
});

test('initial demo state only contains Ozon stores', () => {
  const state = ops.createInitialState();
  assert.ok(state.stores.length > 0);
  assert.ok(state.stores.every((store) => store.platform === 'Ozon'));
});

test('addStore creates an active Ozon store even if another platform is passed', () => {
  const state = ops.createInitialState();
  const next = ops.addStore(state, {
    name: '新加坡跨境店',
    platform: 'Shopify',
    owner: 'Lina',
    authLabel: 'demo-token'
  });
  const created = next.stores.find((store) => store.name === '新加坡跨境店');
  assert.equal(created.platform, 'Ozon');
  assert.equal(created.status, 'active');
  assert.ok(created.id.startsWith('store-'));
});

test('sanitizeOzonState removes non-Ozon stores and related records', () => {
  const state = ops.createInitialState();
  const legacy = {
    ...state,
    stores: [
      ...state.stores,
      { id: 'legacy-store', name: '旧淘宝店', platform: '淘宝', status: 'active', owner: 'Old', authLabel: '旧授权', createdAt: '2026-05-01' }
    ],
    products: [
      ...state.products,
      { id: 'legacy-prod', storeId: 'legacy-store', name: '旧商品', sku: 'OLD', category: '旧类目', price: 1, stock: 1, lowStockThreshold: 1, sales: 1, status: 'on_sale' }
    ],
    orders: [
      ...state.orders,
      { id: 'legacy-order', storeId: 'legacy-store', orderNo: 'OLD', customer: '旧客户', items: [], amount: 1, status: 'paid', shippingStatus: 'pending', carrier: '', trackingNo: '', address: '', note: '', createdAt: '2026-05-30 10:00', shippedAt: '' }
    ],
    promotions: [
      ...state.promotions,
      { id: 'legacy-promo', storeId: 'legacy-store', name: '旧活动', type: 'discount', rule: '旧规则', productIds: ['legacy-prod'], startsAt: '2026-05-30', endsAt: '2026-05-31', status: 'active' }
    ]
  };
  const sanitized = ops.sanitizeOzonState(legacy);
  assert.ok(sanitized.stores.every((store) => store.platform === 'Ozon'));
  assert.equal(sanitized.products.some((product) => product.storeId === 'legacy-store'), false);
  assert.equal(sanitized.orders.some((order) => order.storeId === 'legacy-store'), false);
  assert.equal(sanitized.promotions.some((promotion) => promotion.storeId === 'legacy-store'), false);
});

test('bulkAddOzonStores creates multiple Ozon stores from pasted lines', () => {
  const state = ops.createInitialState();
  const next = ops.bulkAddOzonStores(state, [
    '莫斯科家居店,Ivan,client-001',
    '',
    '圣彼得堡数码店,Anna,client-002',
    '喀山服饰店'
  ].join('\n'));
  const created = next.stores.slice(-3);
  assert.deepEqual(created.map((store) => store.name), ['莫斯科家居店', '圣彼得堡数码店', '喀山服饰店']);
  assert.ok(created.every((store) => store.platform === 'Ozon'));
  assert.equal(created[0].owner, 'Ivan');
  assert.equal(created[2].owner, '未分配');
});

test('parseBulkOzonCredentials parses name client id and api key lines', () => {
  const rows = ops.parseBulkOzonCredentials([
    '莫斯科家居店,1001,key-one',
    '圣彼得堡数码店\t1002\tkey-two',
    'bad-line'
  ].join('\n'));
  assert.deepEqual(rows, [
    { name: '莫斯科家居店', clientId: '1001', apiKey: 'key-one' },
    { name: '圣彼得堡数码店', clientId: '1002', apiKey: 'key-two' }
  ]);
});

test('addBoundOzonStore adds a validated real Ozon store without storing api key', () => {
  const state = ops.createInitialState();
  const next = ops.addBoundOzonStore(state, {
    name: '真实 Ozon 店铺',
    clientId: '123456',
    warehousesCount: 2
  });
  const created = next.stores.find((store) => store.name === '真实 Ozon 店铺');
  assert.equal(created.platform, 'Ozon');
  assert.equal(created.realBound, true);
  assert.equal(created.authLabel, 'Client ID: 123456 · 2 个仓库');
  assert.equal(Object.hasOwn(created, 'apiKey'), false);
});

test('addBoundOzonStore preserves pending verification status', () => {
  const state = ops.createInitialState();
  const next = ops.addBoundOzonStore(state, {
    id: 'store-pending',
    name: '限流待验证店',
    status: 'warning',
    owner: '待验证',
    authLabel: 'Client ID: clie...imit · 待验证',
    realBound: false
  });
  const created = next.stores.find((store) => store.id === 'store-pending');
  assert.equal(created.status, 'warning');
  assert.equal(created.owner, '待验证');
  assert.equal(created.realBound, false);
});

test('mergeBoundOzonStores adds remote stores once and updates status', () => {
  const state = ops.addBoundOzonStore(ops.createInitialState(), {
    id: 'remote-store',
    name: '旧名称',
    status: 'warning',
    owner: '待验证',
    authLabel: 'old',
    realBound: false
  });
  const merged = ops.mergeBoundOzonStores(state, [
    {
      id: 'remote-store',
      name: '新名称',
      status: 'active',
      owner: '真实 API',
      authLabel: 'Client ID: 1234...7890',
      realBound: true
    }
  ]);
  const matches = merged.stores.filter((store) => store.id === 'remote-store');
  assert.equal(matches.length, 1);
  assert.equal(matches[0].name, '新名称');
  assert.equal(matches[0].status, 'active');
});

test('replaceBoundOzonStores keeps only backend stores and scoped records', () => {
  const state = ops.mergeSyncedStoreProducts(ops.createInitialState(), [
    {
      id: 'pub-h1',
      storeId: 'store-h1',
      productId: 'ozon-prod-h1',
      title: 'H1 product',
      sku: 'H1-OFFER',
      offerId: 'H1-OFFER',
      status: 'synced',
      sourceUrl: '',
      priceRub: 499,
      stock: 10
    }
  ]);
  const replaced = ops.replaceBoundOzonStores(state, [
    {
      id: 'store-h1',
      name: 'h1',
      platform: 'Ozon',
      status: 'active',
      owner: '真实 API',
      authLabel: 'Client ID: 4861...1718 · 商品已同步',
      createdAt: '2026-06-02',
      realBound: true,
      verificationError: ''
    }
  ]);
  assert.deepEqual(replaced.stores.map((store) => store.id), ['store-h1']);
  assert.equal(replaced.products.some((product) => product.storeId === 'store-1'), false);
  assert.equal(replaced.orders.some((order) => order.storeId === 'store-1'), false);
  assert.equal(replaced.publishedProducts.some((item) => item.storeId === 'store-1'), false);
  assert.equal(replaced.publishedProducts.some((item) => item.storeId === 'store-h1'), true);
});

test('mergeSyncedStoreProducts adds existing Ozon products without 1688 links', () => {
  const state = ops.createInitialState();
  const merged = ops.mergeSyncedStoreProducts(state, [
    {
      id: 'pub-existing-1',
      storeId: 'store-1',
      productId: 'ozon-prod-1',
      title: 'Ozon existing item',
      sku: 'H1-OFFER-001',
      offerId: 'H1-OFFER-001',
      status: 'synced',
      sourceUrl: '',
      priceRub: 0,
      stock: 0
    }
  ]);
  const product = merged.products.find((item) => item.id === 'ozon-prod-1');
  const published = merged.publishedProducts.find((item) => item.offerId === 'H1-OFFER-001');
  assert.equal(product.name, 'Ozon existing item');
  assert.equal(product.status, 'on_sale');
  assert.equal(published.sourceUrl, '');
  assert.equal(published.status, 'synced');
});

test('updatePublishedProductPrice updates product and published record price', () => {
  const state = ops.mergeSyncedStoreProducts(ops.createInitialState(), [
    {
      id: 'pub-existing-1',
      storeId: 'store-1',
      productId: 'ozon-prod-1',
      title: 'Ozon existing item',
      sku: 'H1-OFFER-001',
      offerId: 'H1-OFFER-001',
      status: 'synced',
      sourceUrl: '',
      priceRub: 499,
      stock: 10
    }
  ]);
  const next = ops.updatePublishedProductPrice(state, 'store-1', 'H1-OFFER-001', 777);
  const product = next.products.find((item) => item.id === 'ozon-prod-1');
  const published = next.publishedProducts.find((item) => item.offerId === 'H1-OFFER-001');
  assert.equal(product.price, 777);
  assert.equal(product.suggestedPriceCny, 777);
  assert.equal(product.suggestedPriceRub, 777);
  assert.equal(published.priceCny, 777);
  assert.equal(published.priceRub, 777);
});

test('canUpdateProductPrice only allows products bound to a real store offer', () => {
  assert.equal(ops.canUpdateProductPrice({
    storeId: 'all',
    sourceOfferId: '853346579651',
    status: 'ready'
  }), false);
  assert.equal(ops.canUpdateProductPrice({
    storeId: 'store-1',
    sourceOfferId: 'xhgxyZq97qBYRZFKnD',
    status: 'on_sale'
  }), true);
  assert.equal(ops.canUpdateProductPrice({
    storeId: 'store-1',
    sourceOfferId: '',
    status: 'on_sale'
  }), false);
});

test('deleteOzonStore removes store scoped records from local state', () => {
  const state = ops.mergeSyncedStoreProducts(ops.createInitialState(), [
    {
      id: 'pub-existing-1',
      storeId: 'store-1',
      productId: 'ozon-prod-1',
      title: 'Ozon existing item',
      sku: 'H1-OFFER-001',
      offerId: 'H1-OFFER-001',
      status: 'synced',
      sourceUrl: '',
      priceRub: 499,
      stock: 10
    }
  ]);
  const next = ops.deleteOzonStore(state, 'store-1');
  assert.equal(next.stores.some((store) => store.id === 'store-1'), false);
  assert.equal(next.orders.some((order) => order.storeId === 'store-1'), false);
  assert.equal(next.publishedProducts.some((item) => item.storeId === 'store-1'), false);
  assert.equal(next.products.some((product) => product.storeId === 'store-1'), false);
});

test('deleteProduct removes one product and its published record from local state', () => {
  const state = ops.mergeSyncedStoreProducts(ops.createInitialState(), [
    {
      id: 'pub-existing-1',
      storeId: 'store-1',
      productId: 'ozon-prod-1',
      title: 'Ozon existing item',
      sku: 'H1-OFFER-001',
      offerId: 'H1-OFFER-001',
      status: 'synced',
      sourceUrl: '',
      priceRub: 499,
      stock: 10
    },
    {
      id: 'pub-existing-2',
      storeId: 'store-1',
      productId: 'ozon-prod-2',
      title: 'Keep me',
      sku: 'H1-OFFER-002',
      offerId: 'H1-OFFER-002',
      status: 'synced',
      sourceUrl: '',
      priceRub: 399,
      stock: 8
    }
  ]);
  state.selectedProducts = new Set(['ozon-prod-1', 'ozon-prod-2']);
  const next = ops.deleteProduct(state, 'store-1', 'H1-OFFER-001');
  assert.equal(next.products.some((product) => product.id === 'ozon-prod-1'), false);
  assert.equal(next.publishedProducts.some((item) => item.offerId === 'H1-OFFER-001'), false);
  assert.equal(next.products.some((product) => product.id === 'ozon-prod-2'), true);
  assert.equal(next.publishedProducts.some((item) => item.offerId === 'H1-OFFER-002'), true);
});

test('delete1688Source removes source and unpublished generated products only', () => {
  const state = ops.createInitialState();
  state.alibabaSources = [
    { id: 'src-1', url: 'https://detail.1688.com/offer/1.html', offerId: '1', title: 'Delete me' },
    { id: 'src-2', url: 'https://detail.1688.com/offer/2.html', offerId: '2', title: 'Keep me' }
  ];
  state.products = [
    { id: 'prod-1', sourceId: 'src-1', storeId: 'all', name: 'Delete product' },
    { id: 'prod-2', sourceId: 'src-2', storeId: 'all', name: 'Keep product' }
  ];
  state.publishedProducts = [];

  const next = ops.delete1688Source(state, 'src-1');

  assert.equal(next.alibabaSources.some((source) => source.id === 'src-1'), false);
  assert.equal(next.products.some((product) => product.id === 'prod-1'), false);
  assert.equal(next.alibabaSources.some((source) => source.id === 'src-2'), true);
  assert.equal(next.products.some((product) => product.id === 'prod-2'), true);
});

test('uniqueProducts collapses duplicate 1688 products by source in the same scope', () => {
  const products = [
    { id: 'prod-1', storeId: 'all', sourceId: 'src-1', sourceOfferId: '739590664908', sku: 'xhDemoSku' },
    { id: 'prod-2', storeId: 'all', sourceId: 'src-1', sourceOfferId: '739590664908', sku: 'xhDemoSku' },
    { id: 'prod-3', storeId: 'store-h1', sourceId: '', sourceOfferId: 'H1-OFFER-001', sku: 'H1-OFFER-001' }
  ];
  const unique = ops.uniqueProducts(products);
  assert.deepEqual(unique.map((product) => product.id), ['prod-1', 'prod-3']);
});

test('shouldCloseModal allows close button and direct backdrop clicks only', () => {
  assert.equal(ops.shouldCloseModal('close-modal', false, false), true);
  assert.equal(ops.shouldCloseModal('close-modal', true, true), true);
  assert.equal(ops.shouldCloseModal('close-modal', true, false), false);
  assert.equal(ops.shouldCloseModal('open-modal', false, false), false);
});

test('filterByScope returns all records or only the selected store records', () => {
  const state = ops.createInitialState();
  assert.equal(ops.filterByScope(state.orders, 'all').length, state.orders.length);
  assert.ok(ops.filterByScope(state.orders, 'store-2').every((order) => order.storeId === 'store-2'));
});

test('paginateRecords clamps page boundaries and reports visible range', () => {
  const records = Array.from({ length: 49 }, (_, index) => ({ id: `prod-${index + 1}` }));

  const first = ops.paginateRecords(records, 0, 20);
  assert.equal(first.page, 1);
  assert.equal(first.totalPages, 3);
  assert.equal(first.start, 1);
  assert.equal(first.end, 20);
  assert.equal(first.items.length, 20);

  const last = ops.paginateRecords(records, 9, 20);
  assert.equal(last.page, 3);
  assert.equal(last.start, 41);
  assert.equal(last.end, 49);
  assert.deepEqual(last.items.map((item) => item.id), records.slice(40).map((item) => item.id));
});

test('deriveMetrics calculates totals for selected scope', () => {
  const state = ops.createInitialState();
  const allMetrics = ops.deriveMetrics(state, 'all');
  const storeMetrics = ops.deriveMetrics(state, 'store-1');
  assert.ok(allMetrics.todayOrders >= storeMetrics.todayOrders);
  assert.ok(allMetrics.pendingShipments >= storeMetrics.pendingShipments);
  assert.ok(allMetrics.lowStockProducts >= storeMetrics.lowStockProducts);
  assert.ok(allMetrics.revenue >= storeMetrics.revenue);
});

test('shipOrders ships pending orders and skips already shipped orders', () => {
  const state = ops.createInitialState();
  const next = ops.shipOrders(state, ['order-1', 'order-3'], '顺丰速运', 'SF123456');
  const shipped = next.orders.find((order) => order.id === 'order-1');
  const skipped = next.orders.find((order) => order.id === 'order-3');
  assert.equal(shipped.shippingStatus, 'shipped');
  assert.equal(shipped.carrier, '顺丰速运');
  assert.equal(shipped.trackingNo, 'SF123456');
  assert.equal(skipped.shippingStatus, 'shipped');
});

test('adjustInventory supports set, increase, decrease and clamps at zero', () => {
  const state = ops.createInitialState();
  const setState = ops.adjustInventory(state, ['prod-1'], 'set', 12);
  assert.equal(setState.products.find((product) => product.id === 'prod-1').stock, 12);
  const increased = ops.adjustInventory(setState, ['prod-1'], 'increase', 5);
  assert.equal(increased.products.find((product) => product.id === 'prod-1').stock, 17);
  const decreased = ops.adjustInventory(increased, ['prod-1'], 'decrease', 99);
  assert.equal(decreased.products.find((product) => product.id === 'prod-1').stock, 0);
});

test('promotionStatus classifies upcoming active ended and draft promotions', () => {
  assert.equal(ops.promotionStatus({ startsAt: '', endsAt: '' }, '2026-05-30'), 'draft');
  assert.equal(ops.promotionStatus({ startsAt: '2026-06-01', endsAt: '2026-06-03' }, '2026-05-30'), 'upcoming');
  assert.equal(ops.promotionStatus({ startsAt: '2026-05-01', endsAt: '2026-06-03' }, '2026-05-30'), 'active');
  assert.equal(ops.promotionStatus({ startsAt: '2026-05-01', endsAt: '2026-05-03' }, '2026-05-30'), 'ended');
});

test('parse1688Urls extracts only valid 1688 offer links', () => {
  const urls = ops.parse1688Urls([
    'https://detail.1688.com/offer/739590664908.html',
    'not a url',
    'https://detail.1688.com/offer/111222333444.html?spm=a'
  ].join('\n'));
  assert.deepEqual(urls, [
    'https://detail.1688.com/offer/739590664908.html',
    'https://detail.1688.com/offer/111222333444.html?spm=a'
  ]);
});

test('calculateSuggestedPrice supports dynamic target margins', () => {
  const lowMargin = ops.calculateSuggestedPrice({ costCny: 34.5, targetMargin: 0.3 });
  const highMargin = ops.calculateSuggestedPrice({ costCny: 34.5, targetMargin: 0.5 });
  assert.equal(Math.round(lowMargin.priceCny), 81);
  assert.equal(Math.round(highMargin.priceCny), 153);
  assert.equal(Math.round(highMargin.priceRub), 153);
  assert.ok(highMargin.priceCny > lowMargin.priceCny);
});

test('add1688Sources and normalize1688Sources create traceable products', () => {
  const state = ops.createInitialState();
  const imported = ops.add1688Sources(state, [
    { id: 'src-1', url: 'https://detail.1688.com/offer/739590664908.html', offerId: '739590664908', title: '民族风方巾', priceMin: 12, status: 'parsed' }
  ]);
  const normalized = ops.normalize1688Sources(imported, ['src-1'], { targetMargin: 0.3 });
  const product = normalized.products.find((item) => item.sourceId === 'src-1');
  assert.equal(product.sourceUrl, 'https://detail.1688.com/offer/739590664908.html');
  assert.equal(product.sourceOfferId, '739590664908');
  assert.match(product.sku, /^xh[A-Za-z0-9]{16}$/);
  assert.equal(product.sku.includes('-'), false);
  assert.ok(product.suggestedPriceCny > 0);
  assert.equal(product.suggestedPriceRub, product.suggestedPriceCny);
});

test('normalize1688Sources inherits matched Ozon category from imported source', () => {
  const state = ops.createInitialState();
  const imported = ops.add1688Sources(state, [
    {
      id: 'src-ozon-cat',
      url: 'https://detail.1688.com/offer/614142976242.html',
      offerId: '614142976242',
      title: '夏季薄刺绣头巾包头发带',
      priceMin: 4.2,
      status: 'parsed',
      ozonCategory: 'Аксессуары для волос',
      ozonCategoryId: '170',
      ozonTypeId: '777'
    }
  ]);
  const normalized = ops.normalize1688Sources(imported, ['src-ozon-cat'], { targetMargin: 0.3 });
  const product = normalized.products.find((item) => item.sourceId === 'src-ozon-cat');
  assert.equal(product.category, 'Аксессуары для волос');
  assert.equal(product.categoryId, '170');
  assert.equal(product.typeId, '777');
  assert.equal(product.validationStatus, 'ready');
});

test('publishProductsToStores records one published product per selected store', () => {
  const state = ops.createInitialState();
  const withSource = ops.add1688Sources(state, [
    {
      id: 'src-1',
      url: 'https://detail.1688.com/offer/739590664908.html',
      offerId: '739590664908',
      title: '民族风方巾',
      priceMin: 12,
      status: 'parsed',
      ozonCategory: 'Аксессуары для волос',
      ozonCategoryId: '170',
      ozonTypeId: '777',
      skus: [{ name: '货号' }, { name: '白色' }]
    }
  ]);
  const normalized = ops.normalize1688Sources(withSource, ['src-1'], { targetMargin: 0.3 });
  const product = normalized.products.find((item) => item.sourceId === 'src-1');
  assert.equal(product.ruTitle, 'Женский платок с принтом');
  const published = ops.publishProductsToStores(normalized, [product.id], ['store-1', 'store-2']);
  const links = published.publishedProducts.filter((item) => item.productId === product.id);
  assert.equal(links.length, 2);
  assert.ok(links.every((item) => item.sourceUrl.includes('1688.com/offer/739590664908.html')));
  assert.ok(links.every((item) => item.offerId === product.sku));
  assert.ok(/^xh[A-Za-z0-9]{16}$/.test(product.sku));
});

test('isPublishRecordVisible hides Ozon synced existing products without import tasks', () => {
  assert.equal(ops.isPublishRecordVisible({ status: 'synced', importTaskId: '' }), false);
  assert.equal(ops.isPublishRecordVisible({ status: 'synced', importTaskId: 'import-123' }), true);
  assert.equal(ops.isPublishRecordVisible({ status: 'submitted', importTaskId: '' }), true);
});

test('canPublishProduct only allows ready 1688 products that are not bound to a concrete store', () => {
  const state = ops.createInitialState();
  const withSource = ops.add1688Sources(state, [
    {
      id: 'src-1',
      url: 'https://detail.1688.com/offer/739590664908.html',
      offerId: '739590664908',
      title: '民族风方巾',
      priceMin: 12,
      status: 'parsed',
      ozonCategory: 'Аксессуары для волос',
      ozonCategoryId: '170',
      ozonTypeId: '777'
    }
  ]);
  const normalized = ops.normalize1688Sources(withSource, ['src-1'], { targetMargin: 0.3 });
  const publishable = normalized.products.find((item) => item.sourceId === 'src-1');
  const synced = {
    ...publishable,
    id: 'ozon-product-1',
    storeId: 'store-1',
    validationStatus: 'synced',
    status: 'on_sale',
    sourceId: 'ozon-store-product'
  };
  const invalid = { ...publishable, id: 'prod-invalid', validationStatus: 'invalid', validationErrors: ['缺少类目'] };

  assert.equal(ops.canPublishProduct(publishable), true);
  assert.equal(ops.canPublishProduct(synced), false);
  assert.equal(ops.canPublishProduct(invalid), false);
});

test('needs review 1688 products show publish entry with review reason', () => {
  const product = {
    storeId: 'all',
    sourceId: 'src-1',
    validationStatus: 'needs_review',
    validationErrors: ['缺少 Ozon 类型 ID']
  };
  assert.equal(ops.canShowPublishEntry(product), true);
  assert.equal(ops.canPublishProduct(product), false);
  assert.equal(ops.productReviewMessage(product), '缺少 Ozon 类型 ID');
});
