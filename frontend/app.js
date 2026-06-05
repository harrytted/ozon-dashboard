(function (root, factory) {
  const api = factory();
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = api;
  }
  if (typeof window !== 'undefined') {
    window.StoreOps = api;
  }
})(this, function () {
  const STORAGE_KEY = 'multi-store-dashboard-state-v1';
  const TODAY = '2026-05-30';
  const PLATFORM_OPTIONS = ['Ozon'];
  const API_BASE_URL = typeof window !== 'undefined'
    ? (window.API_BASE_URL || 'http://127.0.0.1:8000')
    : 'http://127.0.0.1:8000';
  const NON_SELLABLE_SKU_NAMES = new Set([
    '材质', '种类', '风格', '流行元素', '生产编号', '销售序列号', '样式', '造型', '包装',
    '适用送礼场合', '加工定制', '货号', '产地', '主要下游平台', '颜色', '主要销售地区',
    '是否跨境出口专供货源', '上市年份/季节', '加工方式', '编织方法', '品牌', '适用性别',
    '货源类别', '适用年龄段', '适合季节', '图案', '是否外贸', '是否库存', '尺码', '加印LOGO'
  ]);

  function getPlatformOptions() {
    return PLATFORM_OPTIONS.slice();
  }

  function createInitialState() {
    return {
      today: TODAY,
      stores: [
        {
          id: 'store-1',
          name: 'Ozon 莫斯科家居店',
          platform: 'Ozon',
          status: 'active',
          owner: 'Ivan',
          authLabel: 'Ozon Seller ID: 1001',
          createdAt: '2026-04-12'
        },
        {
          id: 'store-2',
          name: 'Ozon 圣彼得堡数码店',
          platform: 'Ozon',
          status: 'active',
          owner: 'Anna',
          authLabel: 'Ozon Seller ID: 1002',
          createdAt: '2026-03-28'
        },
        {
          id: 'store-3',
          name: 'Ozon 喀山服饰店',
          platform: 'Ozon',
          status: 'warning',
          owner: 'Mia',
          authLabel: 'Ozon 授权待刷新',
          createdAt: '2026-05-02'
        }
      ],
      products: [
        {
          id: 'prod-1',
          storeId: 'store-1',
          name: '夏季薄款防晒衬衫',
          sku: 'HZ-SS-1001',
          category: '女装',
          price: 129,
          stock: 8,
          lowStockThreshold: 10,
          sales: 376,
          status: 'on_sale'
        },
        {
          id: 'prod-2',
          storeId: 'store-1',
          name: '高腰直筒牛仔裤',
          sku: 'HZ-JE-2040',
          category: '女装',
          price: 189,
          stock: 46,
          lowStockThreshold: 12,
          sales: 218,
          status: 'on_sale'
        },
        {
          id: 'prod-3',
          storeId: 'store-1',
          name: '通勤小香风外套',
          sku: 'HZ-CO-5518',
          category: '外套',
          price: 329,
          stock: 15,
          lowStockThreshold: 8,
          sales: 92,
          status: 'on_sale'
        },
        {
          id: 'prod-4',
          storeId: 'store-2',
          name: '65W 氮化镓充电器',
          sku: 'SZ-GAN-65',
          category: '数码配件',
          price: 89,
          stock: 6,
          lowStockThreshold: 20,
          sales: 812,
          status: 'on_sale'
        },
        {
          id: 'prod-5',
          storeId: 'store-2',
          name: '蓝牙降噪耳机 Pro',
          sku: 'SZ-BT-PRO',
          category: '音频',
          price: 249,
          stock: 73,
          lowStockThreshold: 15,
          sales: 421,
          status: 'on_sale'
        },
        {
          id: 'prod-6',
          storeId: 'store-2',
          name: '三合一磁吸数据线',
          sku: 'SZ-CB-MAG',
          category: '线材',
          price: 39,
          stock: 0,
          lowStockThreshold: 30,
          sales: 1044,
          status: 'sold_out'
        },
        {
          id: 'prod-7',
          storeId: 'store-3',
          name: '厨房免打孔置物架',
          sku: 'DY-KT-087',
          category: '家居',
          price: 59,
          stock: 25,
          lowStockThreshold: 10,
          sales: 265,
          status: 'on_sale'
        },
        {
          id: 'prod-8',
          storeId: 'store-3',
          name: '便携折叠收纳箱',
          sku: 'DY-BOX-233',
          category: '收纳',
          price: 79,
          stock: 9,
          lowStockThreshold: 12,
          sales: 187,
          status: 'on_sale'
        }
      ],
      orders: [
        {
          id: 'order-1',
          storeId: 'store-1',
          orderNo: 'OZON20260530001',
          customer: '李女士',
          items: [{ productId: 'prod-1', name: '夏季薄款防晒衬衫', qty: 2 }],
          amount: 258,
          status: 'paid',
          shippingStatus: 'pending',
          carrier: '',
          trackingNo: '',
          address: '浙江省杭州市西湖区',
          note: '尽快发货',
          createdAt: '2026-05-30 09:18',
          shippedAt: ''
        },
        {
          id: 'order-2',
          storeId: 'store-1',
          orderNo: 'OZON20260530002',
          customer: '王先生',
          items: [{ productId: 'prod-2', name: '高腰直筒牛仔裤', qty: 1 }],
          amount: 189,
          status: 'paid',
          shippingStatus: 'pending',
          carrier: '',
          trackingNo: '',
          address: '江苏省南京市建邺区',
          note: '',
          createdAt: '2026-05-30 10:04',
          shippedAt: ''
        },
        {
          id: 'order-3',
          storeId: 'store-2',
          orderNo: 'OZON20260529031',
          customer: '周同学',
          items: [{ productId: 'prod-5', name: '蓝牙降噪耳机 Pro', qty: 1 }],
          amount: 249,
          status: 'paid',
          shippingStatus: 'shipped',
          carrier: '圆通速递',
          trackingNo: 'YT923487100',
          address: '广东省广州市天河区',
          note: '',
          createdAt: '2026-05-29 18:43',
          shippedAt: '2026-05-30 08:12'
        },
        {
          id: 'order-4',
          storeId: 'store-2',
          orderNo: 'OZON20260530007',
          customer: '赵先生',
          items: [
            { productId: 'prod-4', name: '65W 氮化镓充电器', qty: 2 },
            { productId: 'prod-6', name: '三合一磁吸数据线', qty: 3 }
          ],
          amount: 295,
          status: 'paid',
          shippingStatus: 'pending',
          carrier: '',
          trackingNo: '',
          address: '四川省成都市高新区',
          note: '一起发',
          createdAt: '2026-05-30 11:21',
          shippedAt: ''
        },
        {
          id: 'order-5',
          storeId: 'store-3',
          orderNo: 'OZON20260530021',
          customer: '许女士',
          items: [{ productId: 'prod-7', name: '厨房免打孔置物架', qty: 1 }],
          amount: 59,
          status: 'paid',
          shippingStatus: 'pending',
          carrier: '',
          trackingNo: '',
          address: '上海市浦东新区',
          note: '',
          createdAt: '2026-05-30 12:08',
          shippedAt: ''
        },
        {
          id: 'order-6',
          storeId: 'store-3',
          orderNo: 'OZON20260528112',
          customer: '林小姐',
          items: [{ productId: 'prod-8', name: '便携折叠收纳箱', qty: 2 }],
          amount: 158,
          status: 'paid',
          shippingStatus: 'exception',
          carrier: '中通快递',
          trackingNo: 'ZT77812003',
          address: '福建省厦门市思明区',
          note: '物流揽收异常',
          createdAt: '2026-05-28 16:35',
          shippedAt: '2026-05-29 10:10'
        },
        {
          id: 'order-7',
          storeId: 'store-1',
          orderNo: 'OZON20260530019',
          customer: 'Alice',
          items: [{ productId: 'prod-3', name: '通勤小香风外套', qty: 1 }],
          amount: 329,
          status: 'paid',
          shippingStatus: 'pending',
          carrier: '',
          trackingNo: '',
          address: '北京市朝阳区',
          note: '',
          createdAt: '2026-05-30 14:27',
          shippedAt: ''
        }
      ],
      promotions: [
        {
          id: 'promo-1',
          storeId: 'store-1',
          name: '女装夏日满减',
          type: 'full_reduction',
          rule: '满 299 减 40',
          productIds: ['prod-1', 'prod-2', 'prod-3'],
          startsAt: '2026-05-20',
          endsAt: '2026-06-10',
          status: 'active'
        },
        {
          id: 'promo-2',
          storeId: 'store-2',
          name: '数码配件限时 9 折',
          type: 'discount',
          rule: '全场 9 折',
          productIds: ['prod-4', 'prod-5', 'prod-6'],
          startsAt: '2026-06-01',
          endsAt: '2026-06-05',
          status: 'upcoming'
        },
        {
          id: 'promo-3',
          storeId: 'store-3',
          name: '直播间收纳专场',
          type: 'limited_time',
          rule: '前 100 件立减 12 元',
          productIds: ['prod-7', 'prod-8'],
          startsAt: '2026-05-28',
          endsAt: '2026-05-30',
          status: 'active'
        }
      ],
      alibabaSources: [],
      publishedProducts: []
    };
  }

  function isSellableSkuName(name) {
    const value = String(name || '').trim();
    return value.length > 1 && !NON_SELLABLE_SKU_NAMES.has(value);
  }

  function sellableSkus(skus) {
    const seen = new Set();
    return (Array.isArray(skus) ? skus : []).filter((item) => {
      const name = String(item && item.name || '').trim();
      if (!isSellableSkuName(name) || seen.has(name)) return false;
      seen.add(name);
      item.name = name;
      return true;
    });
  }

  function heuristicRuTitle(title) {
    const value = String(title || '').trim();
    if (/(头巾|发带|发箍|头套|头饰)/.test(value)) return 'Женская повязка на голову для волос';
    if (/(方巾|围巾|丝巾|披肩)/.test(value)) return 'Женский платок с принтом';
    if (/(凉鞋|拖鞋)/.test(value)) return 'Женские летние сандалии';
    if (/(衬衫|上衣|女装)/.test(value)) return 'Женская блузка';
    return /[\u4e00-\u9fff]/.test(value) ? 'Товар с 1688' : (value || 'Товар с 1688');
  }

  function cloneState(state) {
    return JSON.parse(JSON.stringify(state));
  }

  function filterByScope(records, scope) {
    if (scope === 'all') return records.slice();
    return records.filter((record) => record.storeId === scope);
  }

  function paginateRecords(records, page = 1, pageSize = 20) {
    const items = Array.isArray(records) ? records : [];
    const size = Math.max(1, Number(pageSize) || 20);
    const total = items.length;
    const totalPages = Math.max(1, Math.ceil(total / size));
    const currentPage = Math.min(Math.max(1, Number(page) || 1), totalPages);
    const startIndex = (currentPage - 1) * size;
    const pageItems = items.slice(startIndex, startIndex + size);
    return {
      items: pageItems,
      page: currentPage,
      pageSize: size,
      total,
      totalPages,
      start: total ? startIndex + 1 : 0,
      end: Math.min(startIndex + size, total)
    };
  }

  function promotionStatus(promotion, today) {
    if (!promotion.startsAt || !promotion.endsAt) return 'draft';
    if (today < promotion.startsAt) return 'upcoming';
    if (today > promotion.endsAt) return 'ended';
    return 'active';
  }

  function extract1688OfferId(url) {
    const match = String(url || '').match(/\/offer\/(\d+)\.html/);
    return match ? match[1] : '';
  }

  function parse1688Urls(text) {
    return String(text || '')
      .split(/\s+/)
      .map((part) => part.trim())
      .filter((part) => /^https?:\/\/[^ ]*1688\.com\/offer\/\d+\.html/.test(part));
  }

  function hashSpec(spec) {
    const encoded = JSON.stringify(spec || {}, Object.keys(spec || {}).sort());
    let hash = 0;
    for (let index = 0; index < encoded.length; index += 1) {
      hash = ((hash << 5) - hash + encoded.charCodeAt(index)) >>> 0;
    }
    return hash.toString(36).toUpperCase().padStart(8, '0').slice(0, 8);
  }

  function stableStringify(value) {
    if (Array.isArray(value)) {
      return `[${value.map((item) => stableStringify(item)).join(',')}]`;
    }
    if (value && typeof value === 'object') {
      return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${stableStringify(value[key])}`).join(',')}}`;
    }
    return JSON.stringify(value ?? null);
  }

  function ozonSkuSuffix(value, length = 16) {
    const alphabet = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz';
    let seed = String(value || '');
    let output = '';
    for (let round = 0; output.length < length; round += 1) {
      let hash = 2166136261 ^ round;
      const text = `${seed}:${round}`;
      for (let index = 0; index < text.length; index += 1) {
        hash ^= text.charCodeAt(index);
        hash = Math.imul(hash, 16777619) >>> 0;
      }
      do {
        output += alphabet[hash % alphabet.length];
        hash = Math.floor(hash / alphabet.length);
      } while (hash > 0 && output.length < length);
      seed = `${seed}:${output}`;
    }
    return output.slice(0, length);
  }

  function safeSkuSegment(value, maxLength = 18) {
    const normalized = String(value || '').toUpperCase().replace(/[^A-Z0-9]+/g, '-').replace(/^-|-$/g, '');
    return (normalized || 'SKU').slice(0, maxLength).replace(/-$/g, '') || 'SKU';
  }

  function generateOfferId(storeName, sourceOfferId, spec) {
    return `xh${ozonSkuSuffix(stableStringify({
      store: String(storeName || ''),
      source: String(sourceOfferId || ''),
      spec: spec || {}
    }))}`;
  }

  function calculateSuggestedPrice(input) {
    const costCny = Number(input.costCny || 0);
    const exchangeRate = Number(input.exchangeRate || 10.5);
    const commissionRate = Number(input.commissionRate ?? 0.18);
    const paymentRate = Number(input.paymentRate ?? 0.015);
    const adRate = Number(input.adRate ?? 0.05);
    const returnLossRate = Number(input.returnLossRate ?? 0.03);
    const targetMargin = Number(input.targetMargin ?? 0.3);
    const totalFeeRate = commissionRate + paymentRate + adRate + returnLossRate;
    const denominator = 1 - totalFeeRate - targetMargin;
    if (costCny <= 0 || exchangeRate <= 0 || denominator <= 0) {
      return { fixedCostCny: 0, priceCny: 0, fixedCostRub: 0, priceRub: 0, netMargin: 0, totalFeeRate };
    }
    const fixedCostCny = costCny;
    const priceCny = fixedCostCny / denominator;
    const netProfitCny = priceCny - fixedCostCny - priceCny * totalFeeRate;
    return {
      fixedCostCny,
      priceCny,
      netProfitCny,
      fixedCostRub: fixedCostCny,
      priceRub: priceCny,
      netProfitRub: netProfitCny,
      netMargin: netProfitCny / priceCny,
      totalFeeRate
    };
  }

  function add1688Sources(state, sources) {
    const next = cloneState(state);
    next.alibabaSources = Array.isArray(next.alibabaSources) ? next.alibabaSources : [];
    sources.forEach((source, index) => {
      if (!source.url) return;
      const offerId = source.offerId || extract1688OfferId(source.url);
      const normalized = {
        id: source.id || `src-${Date.now ? Date.now() : next.alibabaSources.length}-${index}`,
        url: source.url,
        offerId,
        title: source.title || `1688 商品 ${offerId}`,
        shopName: source.shopName || '',
        ozonCategory: source.ozonCategory || '',
        ozonCategoryId: source.ozonCategoryId || '0',
        ozonTypeId: source.ozonTypeId || '0',
        ozonCategoryConfidence: Number(source.ozonCategoryConfidence || 0),
        ozonCategoryMatchedBy: source.ozonCategoryMatchedBy || '',
        priceMin: Number(source.priceMin || source.price || 10),
        priceMax: Number(source.priceMax || source.priceMin || source.price || 10),
        images: source.images || [],
        skus: source.skus || [{ name: '默认规格', price: Number(source.priceMin || source.price || 10), stock: 0 }],
        status: source.status || 'parsed',
        error: source.error || '',
        createdAt: source.createdAt || next.today || TODAY
      };
      const existingIndex = next.alibabaSources.findIndex((item) => item.url === normalized.url || item.id === normalized.id);
      if (existingIndex >= 0) {
        next.alibabaSources[existingIndex] = { ...next.alibabaSources[existingIndex], ...normalized };
      } else {
        next.alibabaSources.push(normalized);
      }
    });
    return next;
  }

  function normalize1688Sources(state, sourceIds, options = {}) {
    const next = cloneState(state);
    next.products = Array.isArray(next.products) ? next.products : [];
    const selected = new Set(sourceIds);
    const targetMargin = Number(options.targetMargin ?? 0.3);
    (next.alibabaSources || []).forEach((source) => {
      if (!selected.has(source.id)) return;
      if (next.products.some((product) => product.sourceId === source.id)) return;
      const sourceSkus = sellableSkus(source.skus);
      const skuSpec = sourceSkus[0] || { name: '默认规格', price: Number(source.priceMin || 0), stock: 0 };
      const baseCost = Number(source.priceMin || 10);
      const fullCostCny = baseCost + Number(options.costAddonCny ?? 22.5);
      const quote = calculateSuggestedPrice({ costCny: fullCostCny, targetMargin });
      const sku = generateOfferId('GLOBAL', source.offerId, skuSpec);
      const hasOzonType = Number(source.ozonCategoryId || 0) > 0 && Number(source.ozonTypeId || 0) > 0;
      const validationErrors = hasOzonType ? [] : ['缺少 Ozon 类目 ID', '缺少 Ozon 类型 ID'];
      next.products.push({
        id: `prod-${Date.now ? Date.now() : next.products.length}-${next.products.length + 1}`,
        storeId: 'all',
        sourceId: source.id,
        sourceUrl: source.url,
        sourceOfferId: source.offerId,
        name: source.title,
        ruTitle: heuristicRuTitle(source.title),
        sku,
        category: source.ozonCategory || '1688采集商品',
        categoryId: source.ozonCategoryId || '0',
        typeId: source.ozonTypeId || '0',
        price: Math.round(quote.priceCny),
        suggestedPriceCny: Math.round(quote.priceCny),
        suggestedPriceRub: Math.round(quote.priceCny),
        targetMargin,
        stock: 10,
        lowStockThreshold: 3,
        sales: 0,
        status: hasOzonType ? 'ready' : 'needs_review',
        validationStatus: hasOzonType ? 'ready' : 'needs_review',
        validationErrors,
        attributes: { source_sku: skuSpec }
      });
    });
    return next;
  }

  function publishProductsToStores(state, productIds, storeIds) {
    const next = cloneState(state);
    next.publishedProducts = Array.isArray(next.publishedProducts) ? next.publishedProducts : [];
    const selectedProducts = new Set(productIds);
    const selectedStores = new Set(storeIds);
    next.products.filter((product) => selectedProducts.has(product.id)).forEach((product) => {
      next.stores.filter((store) => selectedStores.has(store.id)).forEach((store) => {
        const offerId = product.sku;
        if (next.publishedProducts.some((item) => item.storeId === store.id && item.offerId === offerId)) return;
        next.publishedProducts.push({
          id: `pub-${Date.now ? Date.now() : next.publishedProducts.length}-${next.publishedProducts.length + 1}`,
          storeId: store.id,
          productId: product.id,
          offerId,
          ozonProductId: '',
          sourceUrl: product.sourceUrl || '',
          status: product.validationStatus === 'ready' ? 'submitted' : 'skipped',
          importTaskId: product.validationStatus === 'ready' ? `local-${offerId}` : '',
          error: product.validationStatus === 'ready' ? '' : (product.validationErrors || []).join('；'),
          priceCny: product.suggestedPriceCny || product.suggestedPriceRub || product.price,
          priceRub: product.suggestedPriceCny || product.suggestedPriceRub || product.price,
          stock: product.stock || 0,
          createdAt: next.today || TODAY
        });
      });
    });
    return next;
  }

  function addNormalizedProducts(state, products) {
    const next = cloneState(state);
    next.products = Array.isArray(next.products) ? next.products : [];
    products.forEach((product) => {
      if (next.products.some((item) => item.id === product.id)) return;
      const source = (next.alibabaSources || []).find((item) => item.id === product.sourceId) || {};
      next.products.push({
        id: product.id,
        storeId: 'all',
        sourceId: product.sourceId,
        sourceUrl: source.url || product.sourceUrl || '',
        sourceOfferId: source.offerId || product.sourceOfferId || '',
        name: product.title,
        ruTitle: product.ruTitle,
        sku: product.sku,
        category: product.category,
        categoryId: product.categoryId || source.ozonCategoryId || '0',
        typeId: product.typeId || source.ozonTypeId || '0',
        attributes: product.attributes || {},
        price: Math.round(product.suggestedPriceCny || product.suggestedPriceRub || 0),
        suggestedPriceCny: Math.round(product.suggestedPriceCny || product.suggestedPriceRub || 0),
        suggestedPriceRub: Math.round(product.suggestedPriceCny || product.suggestedPriceRub || 0),
        targetMargin: product.targetMargin,
        stock: 10,
        lowStockThreshold: 3,
        sales: 0,
        status: product.validationStatus === 'ready' ? 'ready' : 'needs_review',
        validationStatus: product.validationStatus,
        validationErrors: product.validationErrors || []
      });
    });
    return next;
  }

  function deriveMetrics(state, scope) {
    const orders = filterByScope(state.orders, scope);
    const products = filterByScope((state.products || []).filter((product) => product.storeId !== 'all'), scope);
    const promotions = filterByScope(state.promotions, scope);
    const today = state.today || TODAY;
    return {
      todayOrders: orders.filter((order) => order.createdAt.startsWith(today)).length,
      pendingShipments: orders.filter((order) => order.shippingStatus === 'pending').length,
      lowStockProducts: products.filter((product) => product.stock <= product.lowStockThreshold).length,
      activePromotions: promotions.filter((promotion) => promotionStatus(promotion, today) === 'active').length,
      revenue: orders.reduce((total, order) => total + order.amount, 0)
    };
  }

  function addStore(state, storeInput) {
    const next = cloneState(state);
    const nextNumber = next.stores.length + 1;
    next.stores.push({
      id: `store-${Date.now ? Date.now() : nextNumber}-${nextNumber}`,
      name: String(storeInput.name || '').trim(),
      platform: 'Ozon',
      status: 'active',
      owner: String(storeInput.owner || '').trim(),
      authLabel: String(storeInput.authLabel || '演示授权').trim(),
      createdAt: next.today || TODAY
    });
    return next;
  }

  function sanitizeOzonState(state) {
    const fallback = createInitialState();
    if (!state || !Array.isArray(state.stores)) return fallback;

    const next = cloneState({
      today: state.today || TODAY,
      stores: Array.isArray(state.stores) ? state.stores : [],
      products: Array.isArray(state.products) ? state.products : [],
      orders: Array.isArray(state.orders) ? state.orders : [],
      promotions: Array.isArray(state.promotions) ? state.promotions : [],
      alibabaSources: Array.isArray(state.alibabaSources) ? state.alibabaSources : [],
      publishedProducts: Array.isArray(state.publishedProducts) ? state.publishedProducts : []
    });
    next.stores = next.stores.filter((store) => store.platform === 'Ozon');
    if (!next.stores.length) return fallback;

    const ozonStoreIds = new Set(next.stores.map((store) => store.id));
    const ozonProductIds = new Set(
      next.products.filter((product) => ozonStoreIds.has(product.storeId) || product.storeId === 'all').map((product) => product.id)
    );
    next.products = next.products.filter((product) => ozonStoreIds.has(product.storeId) || product.storeId === 'all');
    next.orders = next.orders.filter((order) => ozonStoreIds.has(order.storeId));
    next.promotions = next.promotions
      .filter((promotion) => ozonStoreIds.has(promotion.storeId))
      .map((promotion) => ({
        ...promotion,
        productIds: (promotion.productIds || []).filter((productId) => ozonProductIds.has(productId))
      }));
    next.publishedProducts = next.publishedProducts.filter((item) => ozonStoreIds.has(item.storeId));
    return next;
  }

  function parseBulkOzonStores(text) {
    return String(text || '')
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter(Boolean)
      .map((line) => {
        const [name, owner, authLabel] = line.split(/[,，\t|]/).map((part) => part.trim());
        return {
          name,
          platform: 'Ozon',
          owner: owner || '未分配',
          authLabel: authLabel || 'Ozon 演示授权'
        };
      })
      .filter((store) => store.name);
  }

  function parseBulkOzonCredentials(text) {
    return String(text || '')
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter(Boolean)
      .map((line) => {
        const [name, clientId, apiKey] = line.split(/[,，\t|]/).map((part) => part.trim());
        return { name, clientId, apiKey };
      })
      .filter((store) => store.name && store.clientId && store.apiKey);
  }

  function bulkAddOzonStores(state, text) {
    return parseBulkOzonStores(text).reduce((next, store) => addStore(next, store), state);
  }

  function addBoundOzonStore(state, input) {
    const next = cloneState(state);
    const warehousesCount = Number(input.warehousesCount || 0);
    const store = {
      id: input.id || `ozon-real-${Date.now ? Date.now() : next.stores.length + 1}`,
      name: String(input.name || '').trim(),
      platform: 'Ozon',
      status: input.status || 'active',
      owner: input.owner || '真实 API',
      authLabel: input.authLabel || `Client ID: ${String(input.clientId || '').trim()} · ${warehousesCount} 个仓库`,
      createdAt: input.createdAt || next.today || TODAY,
      realBound: input.realBound !== undefined ? Boolean(input.realBound) : true,
      verificationError: input.verificationError || ''
    };
    const existingIndex = next.stores.findIndex((item) => item.id === store.id);
    if (existingIndex >= 0) {
      next.stores[existingIndex] = { ...next.stores[existingIndex], ...store };
    } else {
      next.stores.push(store);
    }
    return next;
  }

  function mergeBoundOzonStores(state, stores) {
    return (stores || []).reduce((next, store) => addBoundOzonStore(next, store), state);
  }

  function replaceBoundOzonStores(state, stores) {
    const next = cloneState(state);
    const backendStores = (stores || []).filter((store) => store && store.id);
    const storeIds = new Set(backendStores.map((store) => store.id));
    next.stores = backendStores.map((store) => ({
      id: store.id,
      name: String(store.name || '').trim(),
      platform: 'Ozon',
      status: store.status || 'active',
      owner: store.owner || '真实 API',
      authLabel: store.authLabel || 'Ozon 已绑定',
      createdAt: store.createdAt || next.today || TODAY,
      realBound: store.realBound !== undefined ? Boolean(store.realBound) : true,
      verificationError: store.verificationError || ''
    }));
    next.orders = (next.orders || []).filter((order) => storeIds.has(order.storeId));
    next.promotions = (next.promotions || []).filter((promotion) => storeIds.has(promotion.storeId));
    next.publishedProducts = (next.publishedProducts || []).filter((item) => storeIds.has(item.storeId));
    const keptProductIds = new Set(next.publishedProducts.map((item) => item.productId));
    next.products = (next.products || []).filter((product) => product.storeId === 'all' || storeIds.has(product.storeId) || keptProductIds.has(product.id));
    return next;
  }

  function mergeSyncedStoreProducts(state, records) {
    const next = cloneState(state);
    next.products = Array.isArray(next.products) ? next.products : [];
    next.publishedProducts = Array.isArray(next.publishedProducts) ? next.publishedProducts : [];
    (records || []).forEach((record) => {
      const priceCny = Number(record.priceCny ?? record.priceRub ?? 0);
      const product = {
        id: record.productId,
        storeId: record.storeId,
        sourceId: '',
        sourceUrl: record.sourceUrl || '',
        sourceOfferId: record.offerId,
        name: record.title || record.ruTitle || `Ozon 已有商品 ${record.offerId}`,
        ruTitle: record.ruTitle || record.title || '',
        sku: record.sku || record.offerId,
        category: record.category || 'Ozon existing',
        price: priceCny,
        suggestedPriceCny: priceCny,
        suggestedPriceRub: priceCny,
        targetMargin: 0,
        stock: Number(record.stock || 0),
        lowStockThreshold: 0,
        sales: 0,
        status: 'on_sale',
        validationStatus: record.status || 'synced',
        validationErrors: []
      };
      const productIndex = next.products.findIndex((item) => item.id === product.id);
      if (productIndex >= 0) {
        next.products[productIndex] = { ...next.products[productIndex], ...product };
      } else {
        next.products.push(product);
      }

      const published = {
        id: record.id || `${record.storeId}-${record.offerId}`,
        storeId: record.storeId,
        productId: record.productId,
        ozonProductId: record.ozonProductId || '',
        offerId: record.offerId,
        sourceUrl: record.sourceUrl || '',
        status: record.status || 'synced',
        importTaskId: record.importTaskId || '',
        error: record.error || '',
        priceCny,
        priceRub: priceCny,
        stock: Number(record.stock || 0),
        createdAt: record.createdAt || next.today || TODAY
      };
      const publishedIndex = next.publishedProducts.findIndex((item) => item.storeId === published.storeId && item.offerId === published.offerId);
      if (publishedIndex >= 0) {
        next.publishedProducts[publishedIndex] = { ...next.publishedProducts[publishedIndex], ...published };
      } else {
        next.publishedProducts.push(published);
      }
    });
    return next;
  }

  function updatePublishedProductPrice(state, storeId, offerId, priceCny) {
    const next = cloneState(state);
    const numericPrice = Number(priceCny || 0);
    next.publishedProducts = (next.publishedProducts || []).map((item) => {
      if (item.storeId === storeId && item.offerId === offerId) {
        return { ...item, priceCny: numericPrice, priceRub: numericPrice, error: '' };
      }
      return item;
    });
    const published = next.publishedProducts.find((item) => item.storeId === storeId && item.offerId === offerId);
    if (published) {
      next.products = (next.products || []).map((product) => {
        if (product.id === published.productId) {
          return { ...product, price: numericPrice, suggestedPriceCny: numericPrice, suggestedPriceRub: numericPrice };
        }
        return product;
      });
    }
    return next;
  }

  function canUpdateProductPrice(product) {
    return Boolean(
      product
      && product.storeId
      && product.storeId !== 'all'
      && product.sourceOfferId
    );
  }

  function canPublishProduct(product) {
    return Boolean(
      product
      && product.storeId === 'all'
      && product.sourceId
      && product.validationStatus === 'ready'
    );
  }

  function canShowPublishEntry(product) {
    return Boolean(product && product.storeId === 'all' && product.sourceId);
  }

  function productReviewMessage(product) {
    const errors = product && Array.isArray(product.validationErrors) ? product.validationErrors.filter(Boolean) : [];
    if (errors.length) return errors.join('；');
    return '商品需要先补齐 Ozon 类目、Type ID 或必填属性后才能上架';
  }

  function productRecordKey(product) {
    const storeKey = product && product.storeId ? product.storeId : 'all';
    if (product && product.sourceId) return `${storeKey}:source:${product.sourceId}`;
    if (product && product.sourceOfferId) return `${storeKey}:offer:${product.sourceOfferId}`;
    if (product && product.sku) return `${storeKey}:sku:${product.sku}`;
    return `${storeKey}:id:${product ? product.id : ''}`;
  }

  function uniqueProducts(products) {
    const seen = new Set();
    return (products || []).filter((product) => {
      const key = productRecordKey(product);
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }

  function mergePublishJobs(state, jobs) {
    const next = cloneState(state);
    next.publishedProducts = Array.isArray(next.publishedProducts) ? next.publishedProducts : [];
    (jobs || []).forEach((job) => {
      const record = {
        id: job.id || `${job.storeId}-${job.offerId}`,
        storeId: job.storeId,
        productId: job.productId,
        title: job.title || '',
        offerId: job.offerId,
        sourceUrl: job.sourceUrl || '',
        status: job.status || 'submitted',
        importTaskId: job.importTaskId || '',
        error: job.error || '',
        priceCny: job.priceCny ?? job.priceRub ?? 0,
        priceRub: job.priceCny ?? job.priceRub ?? 0,
        stock: job.stock || 0,
        createdAt: job.createdAt || next.today || TODAY
      };
      const index = next.publishedProducts.findIndex((item) => item.storeId === record.storeId && item.offerId === record.offerId);
      if (index >= 0) {
        next.publishedProducts[index] = { ...next.publishedProducts[index], ...record };
      } else {
        next.publishedProducts.push(record);
      }
    });
    return next;
  }

  function deleteOzonStore(state, storeId) {
    const next = cloneState(state);
    const publishedProductIds = new Set((next.publishedProducts || []).filter((item) => item.storeId === storeId).map((item) => item.productId));
    next.stores = (next.stores || []).filter((store) => store.id !== storeId);
    next.orders = (next.orders || []).filter((order) => order.storeId !== storeId);
    next.promotions = (next.promotions || []).filter((promotion) => promotion.storeId !== storeId);
    next.publishedProducts = (next.publishedProducts || []).filter((item) => item.storeId !== storeId);
    next.products = (next.products || []).filter((product) => product.storeId !== storeId && !publishedProductIds.has(product.id));
    return next;
  }

  function deleteProduct(state, storeId, offerId, productId = '') {
    const next = cloneState(state);
    const published = (next.publishedProducts || []).find((item) => {
      const sameStore = !storeId || item.storeId === storeId;
      const sameOffer = !offerId || item.offerId === offerId;
      const sameProduct = !productId || item.productId === productId;
      return sameStore && (sameOffer || sameProduct);
    });
    const targetProductId = productId || (published && published.productId) || '';
    next.publishedProducts = (next.publishedProducts || []).filter((item) => {
      if (published) {
        return !(item.storeId === published.storeId && item.offerId === published.offerId);
      }
      return item.productId !== targetProductId;
    });
    const stillReferenced = new Set((next.publishedProducts || []).map((item) => item.productId));
    next.products = (next.products || []).filter((product) => {
      if (targetProductId && product.id === targetProductId) {
        return stillReferenced.has(product.id);
      }
      return true;
    });
    return next;
  }

  function delete1688Source(state, sourceId) {
    const next = cloneState(state);
    const productIds = new Set((next.products || []).filter((product) => product.sourceId === sourceId).map((product) => product.id));
    const publishedProductIds = new Set((next.publishedProducts || []).map((item) => item.productId));
    next.alibabaSources = (next.alibabaSources || []).filter((source) => source.id !== sourceId);
    next.products = (next.products || []).filter((product) => {
      if (product.sourceId !== sourceId) return true;
      return publishedProductIds.has(product.id);
    });
    next.publishedProducts = (next.publishedProducts || []).filter((item) => !productIds.has(item.productId) || publishedProductIds.has(item.productId));
    return next;
  }

  function scopedStores() {
    const query = ui.query.trim().toLowerCase();
    return (state.stores || []).filter((store) => {
      return !query || [store.name, store.owner, store.authLabel, store.verificationError]
        .some((value) => String(value || '').toLowerCase().includes(query));
    });
  }

  function storeOrderCount(storeId) {
    return state.orders.filter((order) => order.storeId === storeId).length;
  }

  function storeProductCount(storeId) {
    const productKeys = new Set();
    state.products.filter((product) => product.storeId === storeId).forEach((product) => productKeys.add(product.id));
    (state.publishedProducts || []).filter((item) => item.storeId === storeId).forEach((item) => productKeys.add(item.productId || item.offerId));
    return productKeys.size;
  }

  function isUniversalProductTab(tab = ui.tab) {
    return tab === 'import' || tab === 'catalog';
  }

  function mergeTasks(tasks) {
    const current = new Map((ui.tasks || []).map((task) => [task.id, task]));
    (tasks || []).forEach((task) => {
      if (task && task.id) current.set(task.id, { ...(current.get(task.id) || {}), ...task });
    });
    ui.tasks = Array.from(current.values()).sort((a, b) => String(b.updatedAt || b.createdAt || '').localeCompare(String(a.updatedAt || a.createdAt || '')));
  }

  function activeTasks() {
    return (ui.tasks || []).filter((task) => ['queued', 'running'].includes(task.status));
  }

  function runningTaskCount() {
    return activeTasks().length;
  }

  function taskForStore(storeId) {
    return activeTasks().find((task) => task.storeId === storeId);
  }

  function taskKindLabel(kind) {
    const labels = {
      ozon_bind: '绑定店铺',
      ozon_bind_bulk: '批量绑定',
      ozon_products_sync: '同步商品'
    };
    return labels[kind] || kind || '任务';
  }

  function refreshTaskPolling() {
    if (runningTaskCount() && !taskPollTimer) {
      taskPollTimer = window.setInterval(() => refreshTasks(true), 1000);
    }
    if (!runningTaskCount() && taskPollTimer) {
      window.clearInterval(taskPollTimer);
      taskPollTimer = null;
    }
  }

  async function refreshDataForCompletedTask(task) {
    if (!task || task.status !== 'done') return;
    await refreshBoundStores();
    const stores = [];
    if (task.storeId) stores.push({ id: task.storeId });
    if (task.result && Array.isArray(task.result.stores)) {
      task.result.stores.forEach((item) => {
        const store = item.store || {};
        if (store.id) stores.push(store);
      });
    }
    for (const store of stores) {
      await loadStoreProducts(store.id, true);
    }
  }

  async function refreshTasks(silent = false) {
    try {
      const response = await fetch(`${API_BASE_URL}/api/tasks`);
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || '读取任务失败');
      const previousCompleted = new Set(ui.completedTaskIds);
      const wasHydrated = ui.tasksHydrated;
      mergeTasks(result.tasks || []);
      if (!ui.tasksHydrated) {
        ui.tasks.forEach((task) => {
          if (['done', 'failed'].includes(task.status)) ui.completedTaskIds.add(task.id);
        });
        ui.tasksHydrated = true;
      }
      for (const task of ui.tasks) {
        if (wasHydrated && ['done', 'failed'].includes(task.status) && !previousCompleted.has(task.id)) {
          ui.completedTaskIds.add(task.id);
          await refreshDataForCompletedTask(task);
        }
      }
      render();
      refreshTaskPolling();
      return true;
    } catch (error) {
      refreshTaskPolling();
      if (!silent) showToast(error.message || '读取任务失败');
      return false;
    }
  }

  async function createOperationTask(endpoint, payload, successMessage) {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload || {})
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || '创建任务失败');
    mergeTasks([result.task]);
    ui.tasksHydrated = true;
    ui.taskDrawerOpen = true;
    render();
    refreshTaskPolling();
    if (successMessage !== '') showToast(successMessage || '任务已创建');
    return result.task;
  }

  async function refreshBoundStores() {
    try {
      const response = await fetch(`${API_BASE_URL}/api/ozon/stores`);
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || '读取店铺失败');
      state = replaceBoundOzonStores(state, result.stores || []);
      if (ui.scope !== 'all' && !(state.stores || []).some((store) => store.id === ui.scope)) {
        ui.scope = 'all';
      }
      saveState();
      render();
      return true;
    } catch (error) {
      showToast(error.message || '读取本机店铺失败');
      return false;
    }
  }

  async function syncStoreProducts(storeId, silent = false) {
    try {
      await createOperationTask(
        `/api/stores/${storeId}/products/sync-task`,
        {},
        silent ? '' : '商品同步任务已创建'
      );
      return true;
    } catch (error) {
      saveState();
      render();
      showToast(error.message || '同步 Ozon 商品失败');
      return false;
    }
  }

  async function loadStoreProducts(storeId, silent = false) {
    try {
      const response = await fetch(`${API_BASE_URL}/api/stores/${storeId}/products`);
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || '读取店铺商品失败');
      state = mergeSyncedStoreProducts(state, result.products || []);
      saveState();
      render();
      return true;
    } catch (error) {
      if (!silent) showToast(error.message || '读取店铺商品失败');
      return false;
    }
  }

  async function refreshPublishJobs(sync = false, silent = false) {
    try {
      const response = await fetch(`${API_BASE_URL}/api/products/publish-jobs${sync ? '/sync' : ''}`, {
        method: sync ? 'POST' : 'GET'
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || '读取上架任务失败');
      state = mergePublishJobs(state, result.jobs || []);
      saveState();
      render();
      if (!silent) {
        showToast(sync ? `已同步 ${result.checked || 0} 个上架任务` : `已读取 ${result.jobs ? result.jobs.length : 0} 条上架记录`);
      }
      return true;
    } catch (error) {
      if (!silent) showToast(error.message || '读取上架任务失败');
      return false;
    }
  }

  function shouldCloseModal(action, actionElementIsBackdrop, originalTargetIsBackdrop) {
    if (action !== 'close-modal') return false;
    if (actionElementIsBackdrop) return originalTargetIsBackdrop;
    return true;
  }

  function shipOrders(state, orderIds, carrier, trackingNo) {
    const selected = new Set(orderIds);
    const next = cloneState(state);
    next.orders = next.orders.map((order) => {
      if (!selected.has(order.id) || order.shippingStatus === 'shipped') return order;
      return {
        ...order,
        status: 'paid',
        shippingStatus: 'shipped',
        carrier,
        trackingNo,
        shippedAt: `${next.today || TODAY} 15:30`
      };
    });
    return next;
  }

  function adjustInventory(state, productIds, mode, value) {
    const selected = new Set(productIds);
    const numericValue = Number(value);
    const next = cloneState(state);
    next.products = next.products.map((product) => {
      if (!selected.has(product.id)) return product;
      let stock = product.stock;
      if (mode === 'set') stock = numericValue;
      if (mode === 'increase') stock += numericValue;
      if (mode === 'decrease') stock -= numericValue;
      stock = Math.max(0, Math.round(stock));
      return {
        ...product,
        stock,
        status: stock === 0 ? 'sold_out' : 'on_sale'
      };
    });
    return next;
  }

  function addPromotion(state, input) {
    const next = cloneState(state);
    const id = `promo-${Date.now ? Date.now() : next.promotions.length + 1}`;
    next.promotions.push({
      id,
      storeId: input.storeId,
      name: String(input.name || '').trim(),
      type: input.type,
      rule: String(input.rule || '').trim(),
      productIds: input.productIds || [],
      startsAt: input.startsAt,
      endsAt: input.endsAt,
      status: promotionStatus(input, next.today || TODAY)
    });
    return next;
  }

  const api = {
    createInitialState,
    filterByScope,
    paginateRecords,
    deriveMetrics,
    addStore,
    shipOrders,
    adjustInventory,
    addPromotion,
    promotionStatus,
    getPlatformOptions,
    bulkAddOzonStores,
    parseBulkOzonCredentials,
    addBoundOzonStore,
    mergeBoundOzonStores,
    replaceBoundOzonStores,
    mergeSyncedStoreProducts,
    updatePublishedProductPrice,
    canUpdateProductPrice,
    canPublishProduct,
    canShowPublishEntry,
    productReviewMessage,
    productRecordKey,
    uniqueProducts,
    isPublishRecordVisible,
    mergePublishJobs,
    deleteProduct,
    delete1688Source,
    deleteOzonStore,
    sanitizeOzonState,
    shouldCloseModal,
    parse1688Urls,
    calculateSuggestedPrice,
    add1688Sources,
    normalize1688Sources,
    publishProductsToStores,
    addNormalizedProducts,
    generateOfferId
  };

  if (typeof window === 'undefined' || typeof document === 'undefined') {
    return api;
  }

  const ui = {
    scope: 'all',
    tab: 'stores',
    query: '',
    orderStatus: 'all',
    productStatus: 'all',
    productPage: 1,
    productPageSize: 20,
    publishedPage: 1,
    publishedPageSize: 20,
    selectedSources: new Set(),
    selectedOrders: new Set(),
    selectedProducts: new Set(),
    modal: null,
    taskDrawerOpen: false,
    tasks: [],
    completedTaskIds: new Set(),
    tasksHydrated: false,
    toast: ''
  };

  let state = loadState();
  let taskPollTimer = null;

  function loadState() {
    try {
      const stored = window.localStorage.getItem(STORAGE_KEY);
      return stored ? sanitizeOzonState(JSON.parse(stored)) : createInitialState();
    } catch (error) {
      return createInitialState();
    }
  }

  function saveState() {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  }

  function currency(value) {
    return `¥${Number(value).toLocaleString('zh-CN', { minimumFractionDigits: 0 })}`;
  }

  function recordPriceCny(record) {
    return Number(record && (record.priceCny ?? record.priceRub ?? record.price) || 0);
  }

  function productPriceCny(product) {
    return Number(product && (product.suggestedPriceCny ?? product.suggestedPriceRub ?? product.price) || 0);
  }

  function getStoreName(storeId) {
    const store = state.stores.find((item) => item.id === storeId);
    return store ? store.name : '未知店铺';
  }

  function statusLabel(kind, value) {
    const maps = {
      shipping: {
        pending: ['待发货', 'warning'],
        shipped: ['已发货', 'success'],
        exception: ['物流异常', 'danger']
      },
      stock: {
        on_sale: ['在售', 'success'],
        sold_out: ['售罄', 'danger'],
        ready: ['待发布', 'info'],
        needs_review: ['待补齐', 'warning']
      },
      promotion: {
        draft: ['草稿', 'neutral'],
        upcoming: ['未开始', 'info'],
        active: ['进行中', 'success'],
        ended: ['已结束', 'neutral']
      },
      publish: {
        submitted: ['已提交', 'info'],
        processing: ['执行中', 'warning'],
        done: ['已完成', 'success'],
        synced: ['已同步', 'success'],
        failed: ['失败', 'danger'],
        skipped: ['已跳过', 'warning']
      },
      store: {
        active: ['正常', 'success'],
        warning: ['需处理', 'warning']
      }
    };
    const [label, tone] = maps[kind][value] || [value, 'neutral'];
    return `<span class="badge badge-${tone}">${label}</span>`;
  }

  function scopedOrders() {
    return filterByScope(state.orders, ui.scope).filter((order) => {
      const query = ui.query.trim().toLowerCase();
      const statusMatch = ui.orderStatus === 'all' || order.shippingStatus === ui.orderStatus;
      const queryMatch = !query || [order.orderNo, order.customer, getStoreName(order.storeId)]
        .some((value) => value.toLowerCase().includes(query));
      return statusMatch && queryMatch;
    });
  }

  function catalogProducts() {
    return uniqueProducts((state.products || []).filter((product) => product.storeId === 'all')).filter((product) => {
      const query = ui.query.trim().toLowerCase();
      const statusMatch = ui.productStatus === 'all' || product.status === ui.productStatus;
      const queryMatch = !query || [product.name, product.sku, product.category, product.sourceOfferId, product.sourceUrl]
        .some((value) => String(value || '').toLowerCase().includes(query));
      return statusMatch && queryMatch;
    });
  }

  function storeScopedProducts() {
    const storeProducts = (state.products || []).filter((product) => product.storeId && product.storeId !== 'all');
    return uniqueProducts(filterByScope(storeProducts, ui.scope)).filter((product) => {
      const query = ui.query.trim().toLowerCase();
      const statusMatch = ui.productStatus === 'all' || product.status === ui.productStatus;
      const queryMatch = !query || [product.name, product.sku, product.category, getStoreName(product.storeId)]
        .some((value) => String(value || '').toLowerCase().includes(query));
      return statusMatch && queryMatch;
    });
  }

  function scopedProducts(kind = 'store') {
    return kind === 'catalog' ? catalogProducts() : storeScopedProducts();
  }

  function currentProductPageProducts(kind = 'store') {
    return paginateRecords(scopedProducts(kind), ui.productPage, ui.productPageSize).items;
  }

  function scopedPromotions() {
    return filterByScope(state.promotions, ui.scope).filter((promotion) => {
      const query = ui.query.trim().toLowerCase();
      return !query || [promotion.name, promotion.rule, getStoreName(promotion.storeId)]
        .some((value) => value.toLowerCase().includes(query));
    });
  }

  function render() {
    const rootNode = document.getElementById('app');
    rootNode.innerHTML = `
      <aside class="sidebar">
        <div class="brand">
          <div class="brand-mark">多</div>
          <div>
            <h1>Ozon 店铺订单管家</h1>
            <p>1688 采集 · Ozon 上架 · 订单履约</p>
          </div>
        </div>
        <button class="store-card ${ui.scope === 'all' ? 'active' : ''}" data-action="set-scope" data-scope="all">
          <span>全部店铺</span>
          <strong>${state.orders.length} 单</strong>
        </button>
        <div class="store-list">
          ${state.stores.map(renderStoreButton).join('')}
        </div>
        <button class="ghost-button full" data-action="open-modal" data-modal="store">+ 绑定 Ozon 店铺</button>
        <button class="ghost-button full" data-action="open-modal" data-modal="ozon-bulk">批量绑定 Ozon</button>
      </aside>
      <main class="workspace">
        ${renderToolbar()}
        ${isUniversalProductTab() ? '' : renderMetrics()}
        ${renderTabs()}
        ${renderActiveTab()}
      </main>
      ${renderModal()}
      ${renderTaskDrawer()}
      <div class="toast ${ui.toast ? 'show' : ''}">${ui.toast}</div>
    `;
  }

  function renderStoreButton(store) {
    const orders = state.orders.filter((order) => order.storeId === store.id);
    return `
      <button class="store-card ${ui.scope === store.id ? 'active' : ''}" data-action="set-scope" data-scope="${store.id}">
        <span>${store.name}</span>
        <small>${store.platform} · ${store.owner}</small>
        <em>${statusLabel('store', store.status)} ${orders.length} 单</em>
      </button>
    `;
  }

  function renderToolbar() {
    const scopeName = isUniversalProductTab() ? '通用商品池' : (ui.scope === 'all' ? '全部店铺' : getStoreName(ui.scope));
    const activeCount = runningTaskCount();
    return `
      <section class="toolbar">
        <div>
          <p class="eyebrow">当前范围</p>
          <h2>${scopeName}</h2>
        </div>
        <label class="search toolbar-search">
          <span>搜索</span>
          <input data-action="search" value="${escapeHtml(ui.query)}" placeholder="订单号 / 商品 / 店铺 / 客户">
        </label>
        <div class="toolbar-actions">
          <button class="secondary-button task-toggle" data-action="toggle-task-drawer">
            任务${activeCount ? `<span>${activeCount}</span>` : ''}
          </button>
        </div>
      </section>
    `;
  }

  function renderTaskDrawer() {
    const tasks = ui.tasks || [];
    return `
      <aside class="task-drawer ${ui.taskDrawerOpen ? 'open' : ''}">
        <header>
          <div>
            <h3>任务进度</h3>
            <p>${runningTaskCount()} 个进行中</p>
          </div>
          <button class="icon-button" data-action="toggle-task-drawer">×</button>
        </header>
        <div class="task-list">
          ${tasks.length ? tasks.slice(0, 30).map(renderTaskItem).join('') : '<div class="empty compact">暂无任务</div>'}
        </div>
      </aside>
      ${ui.taskDrawerOpen ? '<div class="task-scrim" data-action="toggle-task-drawer"></div>' : ''}
    `;
  }

  function renderTaskItem(task) {
    const progress = Math.max(0, Math.min(100, Number(task.progress || 0)));
    const isFailed = task.status === 'failed';
    return `
      <article class="task-item ${isFailed ? 'failed' : ''}">
        <div class="task-item-head">
          <strong>${escapeHtml(taskKindLabel(task.kind))}</strong>
          ${statusLabel('publish', task.status === 'running' || task.status === 'queued' ? 'processing' : task.status)}
        </div>
        <p>${escapeHtml(task.storeName || task.message || 'Ozon 任务')}</p>
        <div class="progress-row">
          <div class="progress-track"><span style="width:${progress}%"></span></div>
          <em>${progress}%</em>
        </div>
        <small>${escapeHtml(task.currentStep || task.message || '')}</small>
        ${task.error ? `<div class="task-error">${escapeHtml(task.error)}</div>` : ''}
      </article>
    `;
  }

  function renderInlineTaskProgress(task) {
    if (!task) return '';
    const progress = Math.max(0, Math.min(100, Number(task.progress || 0)));
    return `
      <div class="inline-progress">
        <span>${escapeHtml(task.currentStep || task.message || '执行中')}</span>
        <div class="progress-row">
          <div class="progress-track"><span style="width:${progress}%"></span></div>
          <em>${progress}%</em>
        </div>
      </div>
    `;
  }

  function renderMetrics() {
    const metrics = deriveMetrics(state, ui.scope);
    return `
      <section class="metrics">
        <article><span>今日订单</span><strong>${metrics.todayOrders}</strong><small>含全部渠道</small></article>
        <article><span>待发货</span><strong>${metrics.pendingShipments}</strong><small>需要处理</small></article>
        <article><span>库存预警</span><strong>${metrics.lowStockProducts}</strong><small>低于阈值</small></article>
        <article><span>活动中</span><strong>${metrics.activePromotions}</strong><small>促销进行中</small></article>
        <article><span>订单金额</span><strong>${currency(metrics.revenue)}</strong><small>当前范围</small></article>
      </section>
    `;
  }

  function renderTabs() {
    const tabs = [
      ['stores', '店铺'],
      ['import', '1688采集'],
      ['catalog', '通用商品库'],
      ['store-products', '店铺商品'],
      ['orders', '订单'],
      ['published', '上架记录'],
      ['links', '1688绑定'],
      ['inventory', '库存'],
      ['shipping', '物流发货'],
      ['promotions', '促销活动']
    ];
    return `
      <nav class="tabs">
        ${tabs.map(([key, label]) => `
          <button class="${ui.tab === key ? 'active' : ''}" data-action="set-tab" data-tab="${key}">${label}</button>
        `).join('')}
      </nav>
    `;
  }

  function renderActiveTab() {
    if (ui.tab === 'stores') return renderStoresWorkspace();
    if (ui.tab === 'orders') return renderOrders(false);
    if (ui.tab === 'import') return renderImportWorkspace();
    if (ui.tab === 'shipping') return renderOrders(true);
    if (ui.tab === 'catalog') return renderProducts('catalog');
    if (ui.tab === 'store-products') return renderProducts('store');
    if (ui.tab === 'published') return renderPublishedProducts();
    if (ui.tab === 'links') return render1688Links();
    if (ui.tab === 'inventory') return renderProducts('inventory');
    return renderPromotions();
  }

  function renderStoresWorkspace() {
    const stores = scopedStores();
    return `
      <section class="panel">
        <div class="panel-head">
          <div>
            <h3>已绑定 Ozon 店铺</h3>
            <p>查看本机已保存的 Ozon 店铺、验证状态、订单/商品数量和最近一次验证报错。</p>
          </div>
          <div class="controls">
            <button class="secondary-button" data-action="refresh-stores">同步本机绑定</button>
            <button class="primary-button" data-action="open-modal" data-modal="store">绑定 Ozon 店铺</button>
          </div>
        </div>
        ${stores.length ? renderStoresTable(stores) : '<div class="empty">还没有绑定店铺，点击绑定 Ozon 店铺开始。</div>'}
      </section>
    `;
  }

  function renderStoresTable(stores) {
    return `
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>店铺</th>
              <th>状态</th>
              <th>授权</th>
              <th>商品</th>
              <th>订单</th>
              <th>报错信息</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            ${stores.map((store) => {
              const task = taskForStore(store.id);
              return `
              <tr>
                <td><strong>${escapeHtml(store.name)}</strong><br><small>${escapeHtml(store.owner || '未分配')}</small></td>
                <td>${statusLabel('store', store.status)}${renderInlineTaskProgress(task)}</td>
                <td>${escapeHtml(store.authLabel || '未验证')}</td>
                <td>${storeProductCount(store.id)}</td>
                <td>${storeOrderCount(store.id)}</td>
                <td>${store.verificationError ? `<span class="error-text">${escapeHtml(store.verificationError)}</span>` : '<span class="muted-text">无</span>'}</td>
                <td>
                  <button class="link-button" data-action="sync-store-products" data-store-id="${store.id}">${task ? '同步中' : '同步商品'}</button>
                  <button class="link-button" data-action="set-scope" data-scope="${store.id}" data-tab="store-products">查看商品</button>
                  <button class="link-button danger-link" data-action="delete-store" data-store-id="${store.id}">删除</button>
                </td>
              </tr>
            `; }).join('')}
          </tbody>
        </table>
      </div>
    `;
  }

  function scopedSources() {
    const query = ui.query.trim().toLowerCase();
    return (state.alibabaSources || []).filter((source) => {
      return !query || [source.title, source.offerId, source.url, source.shopName, source.ozonCategory]
        .some((value) => String(value || '').toLowerCase().includes(query));
    });
  }

  function publishableProducts() {
    return (state.products || []).filter((product) => canPublishProduct(product));
  }

  function isPublishRecordVisible(record) {
    if (!record) return false;
    return Boolean(record.importTaskId) || record.status !== 'synced';
  }

  function scopedPublishedProducts() {
    const records = ui.scope === 'all'
      ? (state.publishedProducts || [])
      : (state.publishedProducts || []).filter((item) => item.storeId === ui.scope);
    const query = ui.query.trim().toLowerCase();
    return records.filter((item) => {
      if (!isPublishRecordVisible(item)) return false;
      const product = state.products.find((candidate) => candidate.id === item.productId) || {};
      return !query || [item.offerId, item.sourceUrl, product.name, getStoreName(item.storeId)]
        .some((value) => String(value || '').toLowerCase().includes(query));
    });
  }

  function renderImportWorkspace() {
    const sources = scopedSources();
    return `
      <section class="panel">
        <div class="panel-head">
          <div>
            <h3>1688 采集箱</h3>
            <p>导入 1688 商品链接，标准化为 Ozon 可上架商品，保留原始链接绑定关系。</p>
          </div>
          <div class="controls">
            <button class="secondary-button" data-action="rematch-ozon-categories">同步 Ozon 类目</button>
            <button class="secondary-button" data-action="normalize-sources">生成 SKU/定价</button>
            <button class="primary-button" data-action="open-modal" data-modal="1688-import">导入 1688 URL</button>
          </div>
        </div>
        ${sources.length ? renderSourcesTable(sources) : '<div class="empty">还没有 1688 商品，点击导入 1688 URL 开始采集。</div>'}
      </section>
    `;
  }

  function renderSourcesTable(sources) {
    return `
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th><input type="checkbox" data-action="toggle-sources" ${sources.every((source) => ui.selectedSources.has(source.id)) ? 'checked' : ''}></th>
              <th>1688 商品</th>
              <th>Offer ID</th>
              <th>Ozon 类目</th>
              <th>价格</th>
              <th>状态</th>
              <th>来源</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            ${sources.map((source) => `
              <tr>
                <td><input type="checkbox" data-action="select-source" data-id="${source.id}" ${ui.selectedSources.has(source.id) ? 'checked' : ''}></td>
                <td><strong>${escapeHtml(source.title)}</strong><br><small>${escapeHtml(source.shopName || '未识别店铺')}</small></td>
                <td>${escapeHtml(source.offerId)}</td>
                <td>
                  <strong>${escapeHtml(source.ozonCategory || '未匹配')}</strong><br>
                  <small>ID ${escapeHtml(source.ozonCategoryId || '0')} / Type ${escapeHtml(source.ozonTypeId || '0')}</small>
                </td>
                <td>¥${Number(source.priceMin || 0).toFixed(2)}-${Number(source.priceMax || source.priceMin || 0).toFixed(2)}</td>
                <td>${source.status === 'parsed' ? statusLabel('stock', 'on_sale') : statusLabel('store', 'warning')}</td>
                <td><a href="${escapeHtml(source.url)}" target="_blank" rel="noreferrer">1688链接</a></td>
                <td><button class="link-button danger-link" data-action="delete-1688-source" data-source-id="${escapeHtml(source.id)}">删除</button></td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    `;
  }

  function renderPublishedProducts() {
    const records = scopedPublishedProducts();
    const pagination = paginateRecords(records, ui.publishedPage, ui.publishedPageSize);
    ui.publishedPage = pagination.page;
    const products = publishableProducts();
    return `
      <section class="panel">
        <div class="panel-head">
          <div>
            <h3>上架任务与记录</h3>
            <p>查看 Ozon 导入任务 ID、执行状态和失败原因；点击同步可刷新任务完成状态。</p>
          </div>
          <div class="controls">
            <select data-action="published-page-size">
              ${option('10', '每页 10 条', String(ui.publishedPageSize))}
              ${option('20', '每页 20 条', String(ui.publishedPageSize))}
              ${option('50', '每页 50 条', String(ui.publishedPageSize))}
            </select>
            <button class="secondary-button" data-action="refresh-publish-jobs">读取上架任务</button>
            <button class="secondary-button" data-action="sync-publish-jobs">同步任务状态</button>
            <button class="primary-button" data-action="open-modal" data-modal="publish">批量发布到 Ozon</button>
          </div>
        </div>
        ${products.length ? `<p class="form-note">当前可发布商品 ${products.length} 个，已提交记录 ${records.length} 条。</p>` : '<div class="empty">请先在 1688 采集箱生成 SKU/定价。</div>'}
        ${records.length ? renderPublishedTable(pagination.items) : ''}
        ${renderPublishedPagination(pagination)}
      </section>
    `;
  }

  function renderPublishedPagination(pagination) {
    if (!pagination.total) return '';
    const pages = Array.from({ length: pagination.totalPages }, (_, index) => index + 1);
    return `
      <div class="pagination-bar">
        <span>显示 ${pagination.start}-${pagination.end}，共 ${pagination.total} 条上架记录</span>
        <div class="pagination-actions">
          <button class="ghost-button" data-action="published-page" data-page="${pagination.page - 1}" ${pagination.page <= 1 ? 'disabled' : ''}>上一页</button>
          ${pages.map((page) => `
            <button class="${page === pagination.page ? 'primary-button' : 'ghost-button'} page-button" data-action="published-page" data-page="${page}">${page}</button>
          `).join('')}
          <button class="ghost-button" data-action="published-page" data-page="${pagination.page + 1}" ${pagination.page >= pagination.totalPages ? 'disabled' : ''}>下一页</button>
        </div>
      </div>
    `;
  }

  function renderPublishedTable(records) {
    return `
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>店铺</th>
              <th>商品</th>
              <th>Offer ID</th>
              <th>任务 ID</th>
              <th>售价</th>
              <th>状态</th>
              <th>1688链接</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            ${records.map((record) => {
              const product = state.products.find((item) => item.id === record.productId) || {};
              return `
                <tr>
                  <td>${getStoreName(record.storeId)}</td>
                  <td><strong>${escapeHtml(product.name || record.title || record.productId)}</strong>${record.error ? `<br><small class="error-text">${escapeHtml(record.error)}</small>` : ''}</td>
                  <td>${escapeHtml(record.offerId)}</td>
                  <td>${record.importTaskId ? `<code>${escapeHtml(record.importTaskId)}</code>` : '<span class="muted-text">无</span>'}</td>
                  <td>${recordPriceCny(record) ? currency(recordPriceCny(record)) : '-'}</td>
                  <td>${statusLabel('publish', record.status)}</td>
                  <td>${record.sourceUrl ? `<a href="${escapeHtml(record.sourceUrl)}" target="_blank" rel="noreferrer">查看</a>` : '<span class="muted-text">未绑定</span>'}</td>
                  <td><button class="link-button" data-action="open-price-modal" data-store-id="${record.storeId}" data-offer-id="${escapeHtml(record.offerId)}">改价</button></td>
                </tr>
              `;
            }).join('')}
          </tbody>
        </table>
      </div>
    `;
  }

  function render1688Links() {
    const records = scopedPublishedProducts();
    return `
      <section class="panel">
        <div class="panel-head">
          <div>
            <h3>商品与 1688 链接绑定</h3>
            <p>查询每个 Ozon 店铺商品对应的系统 SKU、Ozon offer_id 和 1688 原始商品链接。</p>
          </div>
        </div>
        ${records.length ? renderPublishedTable(records) : '<div class="empty">还没有绑定关系，发布商品后会自动生成。</div>'}
      </section>
    `;
  }

  function renderOrders(shippingOnly) {
    const orders = scopedOrders().filter((order) => !shippingOnly || order.shippingStatus !== 'shipped');
    return `
      <section class="panel">
        <div class="panel-head">
          <div>
            <h3>${shippingOnly ? '物流发货' : '订单管理'}</h3>
            <p>${shippingOnly ? '处理待发货和异常物流订单。' : '查看每个店铺的订单并进入发货流程。'}</p>
          </div>
          <div class="controls">
            <select data-action="order-status">
              ${option('all', '全部状态', ui.orderStatus)}
              ${option('pending', '待发货', ui.orderStatus)}
              ${option('shipped', '已发货', ui.orderStatus)}
              ${option('exception', '物流异常', ui.orderStatus)}
            </select>
            <button class="primary-button" data-action="ship-selected">批量发货</button>
          </div>
        </div>
        ${renderOrdersTable(orders)}
      </section>
    `;
  }

  function renderOrdersTable(orders) {
    if (!orders.length) return '<div class="empty">没有匹配的订单，可以切换店铺或清空筛选。</div>';
    return `
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th><input type="checkbox" data-action="toggle-orders" ${orders.every((order) => ui.selectedOrders.has(order.id)) ? 'checked' : ''}></th>
              <th>订单号</th>
              <th>店铺</th>
              <th>客户</th>
              <th>商品</th>
              <th>金额</th>
              <th>物流</th>
              <th>时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            ${orders.map((order) => `
              <tr>
                <td><input type="checkbox" data-action="select-order" data-id="${order.id}" ${ui.selectedOrders.has(order.id) ? 'checked' : ''}></td>
                <td><strong>${order.orderNo}</strong></td>
                <td>${getStoreName(order.storeId)}</td>
                <td>${order.customer}</td>
                <td>${order.items.map((item) => `${item.name} x${item.qty}`).join('<br>')}</td>
                <td>${currency(order.amount)}</td>
                <td>${statusLabel('shipping', order.shippingStatus)}</td>
                <td>${order.createdAt}</td>
                <td><button class="link-button" data-action="order-detail" data-id="${order.id}">详情</button></td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    `;
  }

  function renderProducts(kind) {
    const isCatalog = kind === 'catalog';
    const inventoryMode = kind === 'inventory';
    const products = scopedProducts(isCatalog ? 'catalog' : 'store');
    const pagination = paginateRecords(products, ui.productPage, ui.productPageSize);
    ui.productPage = pagination.page;
    const title = isCatalog ? '通用商品库' : (inventoryMode ? '批量修改库存' : '店铺商品');
    const description = isCatalog
      ? '由 1688 采集生成，未绑定具体店铺；补齐类目和 Type ID 后可发布到 Ozon 店铺。'
      : (inventoryMode ? '只展示真实店铺商品，选择多个商品后统一设置、增加或减少库存。' : '按店铺查看 Ozon 已同步或已上架的商品、SKU、价格和库存。');
    return `
      <section class="panel">
        <div class="panel-head compact-head">
          <div>
            <h3>${title}</h3>
            <p>${description}</p>
          </div>
          <div class="controls compact-controls">
            <select data-action="product-status">
              ${option('all', '全部商品', ui.productStatus)}
              ${isCatalog ? option('ready', '可上架', ui.productStatus) : ''}
              ${isCatalog ? option('needs_review', '待补齐', ui.productStatus) : ''}
              ${option('on_sale', '在售', ui.productStatus)}
              ${option('sold_out', '售罄', ui.productStatus)}
            </select>
            <select data-action="product-page-size">
              ${option('10', '每页 10 个', String(ui.productPageSize))}
              ${option('20', '每页 20 个', String(ui.productPageSize))}
              ${option('50', '每页 50 个', String(ui.productPageSize))}
            </select>
            ${isCatalog ? `<button class="primary-button" data-action="open-modal" data-modal="publish">批量发布到 Ozon</button>` : `<button class="primary-button" data-action="inventory-selected">批量改库存</button>`}
          </div>
        </div>
        ${renderProductsTable(pagination.items, isCatalog ? 'catalog' : 'store')}
        ${renderProductPagination(pagination)}
      </section>
    `;
  }

  function renderProductPagination(pagination) {
    if (!pagination.total) return '';
    const pages = Array.from({ length: pagination.totalPages }, (_, index) => index + 1);
    return `
      <div class="pagination-bar">
        <span>显示 ${pagination.start}-${pagination.end}，共 ${pagination.total} 个商品</span>
        <div class="pagination-actions">
          <button class="ghost-button" data-action="product-page" data-page="${pagination.page - 1}" ${pagination.page <= 1 ? 'disabled' : ''}>上一页</button>
          ${pages.map((page) => `
            <button class="${page === pagination.page ? 'primary-button' : 'ghost-button'} page-button" data-action="product-page" data-page="${page}">${page}</button>
          `).join('')}
          <button class="ghost-button" data-action="product-page" data-page="${pagination.page + 1}" ${pagination.page >= pagination.totalPages ? 'disabled' : ''}>下一页</button>
        </div>
      </div>
    `;
  }

  function renderProductsTable(products, kind = 'store') {
    const isCatalog = kind === 'catalog';
    if (!products.length) {
      return `<div class="empty">${isCatalog ? '通用商品库暂无商品，请先在 1688 采集箱生成 SKU/定价。' : '没有匹配的店铺商品，可以切换店铺或清空筛选。'}</div>`;
    }
    return `
      <div class="table-wrap product-table-wrap">
        <table class="product-table ${isCatalog ? 'catalog-product-table' : ''}">
          <thead>
            <tr>
              <th><input type="checkbox" data-action="toggle-products" ${products.every((product) => ui.selectedProducts.has(product.id)) ? 'checked' : ''}></th>
              <th>商品</th>
              ${isCatalog ? '<th>1688 来源</th>' : '<th>店铺</th>'}
              <th>SKU</th>
              <th>分类</th>
              <th>价格</th>
              ${isCatalog ? '<th>Type ID</th>' : '<th>库存</th>'}
              ${isCatalog ? '<th>1688货号</th>' : '<th>销量</th>'}
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            ${products.map((product) => `
              <tr class="${product.stock <= product.lowStockThreshold ? 'row-warning' : ''}">
                <td><input type="checkbox" data-action="select-product" data-id="${product.id}" ${ui.selectedProducts.has(product.id) ? 'checked' : ''}></td>
                <td><strong>${product.name}</strong></td>
                <td>${isCatalog ? `<a href="${escapeHtml(product.sourceUrl || '#')}" target="_blank" rel="noreferrer">1688链接</a>` : getStoreName(product.storeId)}</td>
                <td>${escapeHtml(product.sku || '-')}</td>
                <td>${escapeHtml(product.category || '-')}</td>
                <td>${productPriceCny(product) ? currency(productPriceCny(product)) : '-'}</td>
                <td>${isCatalog ? escapeHtml(product.typeId || '0') : `${product.stock} <small>/ 预警 ${product.lowStockThreshold}</small>`}</td>
                <td>${isCatalog ? escapeHtml(product.sourceOfferId || '-') : product.sales}</td>
                <td>${statusLabel('stock', product.status)}</td>
                <td>
                  ${!isCatalog && canUpdateProductPrice(product) ? `<button class="link-button" data-action="open-price-modal" data-store-id="${product.storeId}" data-offer-id="${escapeHtml(product.sourceOfferId)}">改价</button>` : ''}
                  ${canShowPublishEntry(product) ? `<button class="link-button" data-action="open-publish-product" data-product-id="${escapeHtml(product.id)}">上架</button>` : ''}
                  ${!canUpdateProductPrice(product) && !canShowPublishEntry(product) ? '<span class="muted-text">未上架</span>' : ''}
                  <button class="link-button danger-link" data-action="delete-product" data-store-id="${product.storeId}" data-offer-id="${escapeHtml(product.sourceOfferId || '')}" data-product-id="${escapeHtml(product.id)}">删除</button>
                </td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    `;
  }

  function renderPromotions() {
    const promotions = scopedPromotions();
    return `
      <section class="panel">
        <div class="panel-head">
          <div>
            <h3>促销活动</h3>
            <p>新增满减、折扣和限时活动，并按店铺查看状态。</p>
          </div>
          <button class="primary-button" data-action="open-modal" data-modal="promotion">新增促销活动</button>
        </div>
        ${promotions.length ? `
          <div class="promo-grid">
            ${promotions.map((promotion) => {
              const status = promotionStatus(promotion, state.today);
              return `
                <article class="promo-card">
                  <div>
                    <h4>${promotion.name}</h4>
                    <p>${getStoreName(promotion.storeId)}</p>
                  </div>
                  ${statusLabel('promotion', status)}
                  <strong>${promotion.rule}</strong>
                  <span>${promotion.startsAt || '未设置'} 至 ${promotion.endsAt || '未设置'}</span>
                </article>
              `;
            }).join('')}
          </div>
        ` : '<div class="empty">还没有促销活动，点击新增促销活动创建一个。</div>'}
      </section>
    `;
  }

  function renderModal() {
    if (!ui.modal) return '';
    const titleMap = {
      store: '绑定 Ozon 店铺',
      ship: '物流发货',
      inventory: '批量修改库存',
      promotion: '新增促销活动',
      'ozon-bulk': '批量绑定 Ozon 店铺',
      '1688-import': '导入 1688 商品',
      publish: '批量发布到 Ozon',
      price: '修改 Ozon 价格',
      order: '订单详情'
    };
    return `
      <div class="modal-backdrop" data-action="close-modal">
        <section class="modal">
          <header>
            <h3>${titleMap[ui.modal.type]}</h3>
            <button class="icon-button" data-action="close-modal">×</button>
          </header>
          ${renderModalBody()}
        </section>
      </div>
    `;
  }

  function renderModalBody() {
    if (ui.modal.type === 'store') {
      return `
        <form data-form="store" class="form-grid">
          <p class="form-note">请输入 Ozon Seller 后台生成的 Client ID 和 API Key。密钥只发送到本机 localhost 代理，不写入前端代码或浏览器状态。</p>
          <label>Ozon 店铺名称<input name="name" required placeholder="例如：Ozon 莫斯科家居店"></label>
          <label>Client ID<input name="clientId" required inputmode="numeric" autocomplete="off" placeholder="Ozon Seller Client ID"></label>
          <label>API Key<input name="apiKey" required type="password" autocomplete="off" placeholder="Ozon Seller API Key"></label>
          <button class="primary-button wide" type="submit">验证并绑定 Ozon 店铺</button>
        </form>
      `;
    }
    if (ui.modal.type === 'ship') {
      return `
        <form data-form="ship" class="form-grid">
          <p class="form-note">将为 ${ui.selectedOrders.size} 个已选订单填写物流信息。已发货订单会被自动跳过。</p>
          <label>物流公司<input name="carrier" required placeholder="例如：顺丰速运"></label>
          <label>物流单号<input name="trackingNo" required placeholder="例如：SF123456789"></label>
          <button class="primary-button wide" type="submit">确认发货</button>
        </form>
      `;
    }
    if (ui.modal.type === 'ozon-bulk') {
      return `
        <form data-form="ozon-bulk" class="form-grid">
          <p class="form-note">一行一个 Ozon 店铺，格式：店铺名称,Client ID,API Key。密钥只发送到本机后端，不写入浏览器状态。</p>
          <label>店铺列表
            <textarea name="stores" required rows="8" placeholder="莫斯科家居店,1001001,ozon-api-key-1&#10;圣彼得堡数码店,1001002,ozon-api-key-2"></textarea>
          </label>
          <label class="check-row"><input name="autoSyncProducts" type="checkbox"> 绑定后自动同步商品</label>
          <button class="primary-button wide" type="submit">批量绑定 Ozon 店铺</button>
        </form>
      `;
    }
    if (ui.modal.type === '1688-import') {
      return `
        <form data-form="1688-import" class="form-grid">
          <p class="form-note">一行一个 1688 商品链接。系统会优先调用本地后端采集，失败时按链接生成待复核来源。</p>
          <label>1688 商品链接
            <textarea name="urls" required rows="8" placeholder="https://detail.1688.com/offer/739590664908.html&#10;https://detail.1688.com/offer/111222333444.html"></textarea>
          </label>
          <button class="primary-button wide" type="submit">开始采集</button>
        </form>
      `;
    }
    if (ui.modal.type === 'publish') {
      const products = publishableProducts();
      const selectedProductIds = new Set(ui.modal.productIds && ui.modal.productIds.length ? ui.modal.productIds : products.map((product) => product.id));
      const selectedStoreIds = new Set(ui.modal.storeIds && ui.modal.storeIds.length
        ? ui.modal.storeIds
        : state.stores.filter((store) => ui.scope === 'all' || ui.scope === store.id).map((store) => store.id));
      return `
        <form data-form="publish" class="form-grid">
          <p class="form-note">选择商品和 Ozon 店铺。通过校验的商品会提交发布；失败商品保留原因。</p>
          <label>商品
            <select name="productIds" multiple size="6" required>
              ${products.map((product) => `<option value="${product.id}" ${selectedProductIds.has(product.id) ? 'selected' : ''}>${escapeHtml(product.name)} · ${escapeHtml(product.sku)}</option>`).join('')}
            </select>
          </label>
          <label>店铺
            <select name="storeIds" multiple size="6" required>
              ${state.stores.map((store) => `<option value="${store.id}" ${selectedStoreIds.has(store.id) ? 'selected' : ''}>${escapeHtml(store.name)}</option>`).join('')}
            </select>
          </label>
          <button class="primary-button wide" type="submit">${ui.modal.productIds && ui.modal.productIds.length === 1 ? '发布到选中店铺' : '批量发布'}</button>
        </form>
      `;
    }
    if (ui.modal.type === 'price') {
      const record = (state.publishedProducts || []).find((item) => item.storeId === ui.modal.storeId && item.offerId === ui.modal.offerId) || {};
      const product = state.products.find((item) => item.id === record.productId) || {};
      return `
        <form data-form="price" class="form-grid">
          <p class="form-note">${escapeHtml(getStoreName(ui.modal.storeId))} · ${escapeHtml(product.name || record.offerId || '')}</p>
          <label>Offer ID<input name="offerId" readonly value="${escapeHtml(ui.modal.offerId || '')}"></label>
          <label>新售价 CNY<input name="priceCny" type="number" min="1" step="0.01" required value="${recordPriceCny(record) || productPriceCny(product)}"></label>
          <label>划线价 CNY<input name="oldPriceCny" type="number" min="0" step="0.01" placeholder="可选，不填则不改"></label>
          <label>最低价 CNY<input name="minPriceCny" type="number" min="0" step="0.01" placeholder="可选，不填则不改"></label>
          <button class="primary-button wide" type="submit">提交改价</button>
        </form>
      `;
    }
    if (ui.modal.type === 'inventory') {
      return `
        <form data-form="inventory" class="form-grid">
          <p class="form-note">将修改 ${ui.selectedProducts.size} 个已选商品库存，结果不会小于 0。</p>
          <label>调整方式
            <select name="mode" required>
              <option value="set">设置为</option>
              <option value="increase">增加</option>
              <option value="decrease">减少</option>
            </select>
          </label>
          <label>数量<input name="value" type="number" min="0" step="1" required value="10"></label>
          <button class="primary-button wide" type="submit">应用库存修改</button>
        </form>
      `;
    }
    if (ui.modal.type === 'promotion') {
      return `
        <form data-form="promotion" class="form-grid">
          <label>活动名称<input name="name" required placeholder="例如：618 限时折扣"></label>
          <label>活动店铺
            <select name="storeId" required>
              ${state.stores.map((store) => `<option value="${store.id}" ${ui.scope === store.id ? 'selected' : ''}>${store.name}</option>`).join('')}
            </select>
          </label>
          <label>活动类型
            <select name="type" required>
              <option value="discount">折扣</option>
              <option value="full_reduction">满减</option>
              <option value="limited_time">限时活动</option>
            </select>
          </label>
          <label>活动规则<input name="rule" required placeholder="例如：满 199 减 30"></label>
          <label>开始日期<input name="startsAt" type="date" required value="${state.today}"></label>
          <label>结束日期<input name="endsAt" type="date" required value="${state.today}"></label>
          <button class="primary-button wide" type="submit">创建活动</button>
        </form>
      `;
    }
    if (ui.modal.type === 'order') {
      const order = state.orders.find((item) => item.id === ui.modal.id);
      return `
        <div class="detail">
          <p><span>店铺</span><strong>${getStoreName(order.storeId)}</strong></p>
          <p><span>客户</span><strong>${order.customer}</strong></p>
          <p><span>地址</span><strong>${order.address}</strong></p>
          <p><span>商品</span><strong>${order.items.map((item) => `${item.name} x${item.qty}`).join('，')}</strong></p>
          <p><span>金额</span><strong>${currency(order.amount)}</strong></p>
          <p><span>物流</span><strong>${statusLabel('shipping', order.shippingStatus)} ${order.carrier || ''} ${order.trackingNo || ''}</strong></p>
          <p><span>备注</span><strong>${order.note || '无'}</strong></p>
        </div>
      `;
    }
    return '';
  }

  function option(value, label, selected) {
    return `<option value="${value}" ${value === selected ? 'selected' : ''}>${label}</option>`;
  }

  function showToast(message) {
    ui.toast = message;
    render();
    window.setTimeout(() => {
      ui.toast = '';
      render();
    }, 1800);
  }

  function escapeHtml(value) {
    return String(value).replace(/[&<>"']/g, (char) => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#039;'
    })[char]);
  }

  async function handleClick(event) {
    const target = event.target.closest('[data-action]');
    if (!target) return;
    const action = target.dataset.action;
    if (action === 'set-scope') {
      ui.scope = target.dataset.scope;
      if (target.dataset.tab) ui.tab = target.dataset.tab;
      ui.selectedOrders.clear();
      ui.selectedProducts.clear();
      ui.productPage = 1;
      ui.publishedPage = 1;
      if ((ui.tab === 'store-products' || ui.tab === 'inventory') && ui.scope !== 'all') {
        await loadStoreProducts(ui.scope, true);
      } else {
        render();
      }
    }
    if (action === 'set-tab') {
      ui.tab = target.dataset.tab;
      ui.selectedProducts.clear();
      if (isUniversalProductTab(ui.tab)) ui.scope = 'all';
      if (ui.tab === 'catalog' || ui.tab === 'store-products' || ui.tab === 'inventory') {
        ui.productPage = 1;
        ui.productStatus = 'all';
      }
      if (ui.tab === 'published') {
        ui.publishedPage = 1;
        await refreshPublishJobs(false, true);
      }
      if ((ui.tab === 'store-products' || ui.tab === 'inventory') && ui.scope !== 'all') {
        await loadStoreProducts(ui.scope, true);
      } else {
        render();
      }
    }
    if (action === 'open-modal') {
      if (target.dataset.modal === 'publish') {
        const selectedPublishableIds = Array.from(ui.selectedProducts).filter((productId) => {
          const product = state.products.find((item) => item.id === productId);
          return canPublishProduct(product);
        });
        ui.modal = selectedPublishableIds.length
          ? { type: 'publish', productIds: selectedPublishableIds }
          : { type: 'publish' };
      } else {
        ui.modal = { type: target.dataset.modal };
      }
      render();
    }
    if (action === 'toggle-task-drawer') {
      ui.taskDrawerOpen = !ui.taskDrawerOpen;
      render();
    }
    if (action === 'open-price-modal') {
      const product = state.products.find((item) => item.storeId === target.dataset.storeId && item.sourceOfferId === target.dataset.offerId);
      if (!canUpdateProductPrice(product)) return showToast('商品未上架到具体店铺，不能改价');
      ui.modal = { type: 'price', storeId: target.dataset.storeId, offerId: target.dataset.offerId };
      render();
    }
    if (action === 'open-publish-product') {
      const productId = target.dataset.productId || '';
      const product = state.products.find((item) => item.id === productId);
      if (!canPublishProduct(product)) return showToast(productReviewMessage(product));
      ui.modal = { type: 'publish', productIds: [productId] };
      render();
    }
    if (action === 'refresh-stores') {
      await refreshBoundStores();
    }
    if (action === 'sync-store-products') {
      await syncStoreProducts(target.dataset.storeId);
    }
    if (action === 'delete-store') {
      const storeId = target.dataset.storeId;
      const storeName = getStoreName(storeId);
      if (!window.confirm(`确认删除店铺「${storeName}」？本地订单、商品和上架记录会一起移除。`)) return;
      try {
        const response = await fetch(`${API_BASE_URL}/api/ozon/stores/${storeId}`, { method: 'DELETE' });
        const result = await response.json();
        if (!response.ok) throw new Error(result.error || '删除店铺失败');
        state = deleteOzonStore(state, storeId);
        if (ui.scope === storeId) ui.scope = 'all';
        ui.tab = 'stores';
        saveState();
        showToast('店铺已删除');
      } catch (error) {
        showToast(error.message || '删除店铺失败');
      }
    }
    if (action === 'delete-product') {
      const storeId = target.dataset.storeId || '';
      const offerId = target.dataset.offerId || '';
      const productId = target.dataset.productId || '';
      const product = state.products.find((item) => item.id === productId) || {};
      if (!window.confirm(`确认删除商品「${product.name || offerId || productId}」？本地商品和上架记录会移除。`)) return;
      try {
        if (storeId && storeId !== 'all' && offerId) {
          const response = await fetch(`${API_BASE_URL}/api/stores/${storeId}/products/${encodeURIComponent(offerId)}`, { method: 'DELETE' });
          const result = await response.json();
          if (!response.ok) throw new Error(result.error || '删除商品失败');
        }
        state = deleteProduct(state, storeId, offerId, productId);
        ui.selectedProducts.delete(productId);
        saveState();
        showToast('商品已删除');
      } catch (error) {
        showToast(error.message || '删除商品失败');
      }
    }
    if (action === 'delete-1688-source') {
      const sourceId = target.dataset.sourceId || '';
      const source = (state.alibabaSources || []).find((item) => item.id === sourceId) || {};
      if (!window.confirm(`确认删除采集商品「${source.title || source.offerId || sourceId}」？未上架的 SKU/定价商品也会一起移除。`)) return;
      try {
        const response = await fetch(`${API_BASE_URL}/api/1688/sources/${encodeURIComponent(sourceId)}`, { method: 'DELETE' });
        const result = await response.json();
        if (!response.ok) throw new Error(result.error || '删除采集商品失败');
      } catch (error) {
        if (String(error.message || '').includes('已有上架记录')) return showToast(error.message);
      }
      state = delete1688Source(state, sourceId);
      ui.selectedSources.delete(sourceId);
      saveState();
      showToast('采集商品已删除');
    }
    if (shouldCloseModal(action, target.classList.contains('modal-backdrop'), event.target === target)) {
      ui.modal = null;
      render();
    }
    if (action === 'ship-selected') {
      if (!ui.selectedOrders.size) return showToast('请先选择要发货的订单');
      ui.modal = { type: 'ship' };
      render();
    }
    if (action === 'inventory-selected') {
      if (!ui.selectedProducts.size) return showToast('请先选择要修改库存的商品');
      ui.modal = { type: 'inventory' };
      render();
    }
    if (action === 'product-page') {
      ui.productPage = Number(target.dataset.page || 1);
      render();
    }
    if (action === 'published-page') {
      ui.publishedPage = Number(target.dataset.page || 1);
      render();
    }
    if (action === 'refresh-publish-jobs') {
      await refreshPublishJobs(false);
    }
    if (action === 'sync-publish-jobs') {
      await refreshPublishJobs(true);
    }
    if (action === 'normalize-sources') {
      if (!ui.selectedSources.size) return showToast('请先选择 1688 商品源');
      const sourceIds = Array.from(ui.selectedSources);
      try {
        const response = await fetch(`${API_BASE_URL}/api/products/normalize`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ sourceIds, targetMargin: 0.3 })
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.error || '标准化失败');
        state = addNormalizedProducts(state, result.products || []);
      } catch (error) {
        state = normalize1688Sources(state, sourceIds, { targetMargin: 0.3 });
      }
      ui.selectedSources.clear();
      ui.tab = 'products';
      saveState();
      showToast('已生成 SKU、建议价和俄语文案');
    }
    if (action === 'rematch-ozon-categories') {
      const sourceIds = Array.from(ui.selectedSources);
      try {
        const response = await fetch(`${API_BASE_URL}/api/1688/rematch-categories`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ sourceIds })
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.error || '同步 Ozon 类目失败');
        state = add1688Sources(state, result.sources || []);
        saveState();
        render();
        showToast(`已同步 ${result.matched || 0}/${result.checked || 0} 个 Ozon 类目`);
      } catch (error) {
        showToast(error.message || '同步 Ozon 类目失败，请确认后端可访问 Ozon API');
      }
    }
    if (action === 'order-detail') {
      ui.modal = { type: 'order', id: target.dataset.id };
      render();
    }
  }

  function handleChange(event) {
    const target = event.target;
    const action = target.dataset.action;
    if (action === 'order-status') {
      ui.orderStatus = target.value;
      render();
    }
    if (action === 'product-status') {
      ui.productStatus = target.value;
      ui.productPage = 1;
      render();
    }
    if (action === 'product-page-size') {
      ui.productPageSize = Number(target.value || 20);
      ui.productPage = 1;
      render();
    }
    if (action === 'published-page-size') {
      ui.publishedPageSize = Number(target.value || 20);
      ui.publishedPage = 1;
      render();
    }
    if (action === 'select-order') {
      target.checked ? ui.selectedOrders.add(target.dataset.id) : ui.selectedOrders.delete(target.dataset.id);
      render();
    }
    if (action === 'select-product') {
      target.checked ? ui.selectedProducts.add(target.dataset.id) : ui.selectedProducts.delete(target.dataset.id);
      render();
    }
    if (action === 'select-source') {
      target.checked ? ui.selectedSources.add(target.dataset.id) : ui.selectedSources.delete(target.dataset.id);
      render();
    }
    if (action === 'toggle-orders') {
      scopedOrders().forEach((order) => {
        target.checked ? ui.selectedOrders.add(order.id) : ui.selectedOrders.delete(order.id);
      });
      render();
    }
    if (action === 'toggle-products') {
      const kind = ui.tab === 'catalog' ? 'catalog' : 'store';
      currentProductPageProducts(kind).forEach((product) => {
        target.checked ? ui.selectedProducts.add(product.id) : ui.selectedProducts.delete(product.id);
      });
      render();
    }
    if (action === 'toggle-sources') {
      scopedSources().forEach((source) => {
        target.checked ? ui.selectedSources.add(source.id) : ui.selectedSources.delete(source.id);
      });
      render();
    }
  }

  function handleInput(event) {
    if (event.target.dataset.action === 'search') {
      ui.query = event.target.value;
      ui.productPage = 1;
      ui.publishedPage = 1;
      render();
      const searchInput = document.querySelector('[data-action="search"]');
      searchInput.focus();
      searchInput.setSelectionRange(ui.query.length, ui.query.length);
    }
  }

  async function handleSubmit(event) {
    const form = event.target.closest('form[data-form]');
    if (!form) return;
    event.preventDefault();
    const data = Object.fromEntries(new FormData(form));
    if (form.dataset.form === 'store') {
      try {
        ui.tab = 'stores';
        ui.modal = null;
        saveState();
        await createOperationTask('/api/ozon/bind-task', data, '店铺绑定任务已创建');
      } catch (error) {
        showToast(error.message || '请使用 node server.js 启动本地代理后再绑定');
      }
    }
    if (form.dataset.form === 'ship') {
      state = shipOrders(state, Array.from(ui.selectedOrders), data.carrier, data.trackingNo);
      ui.selectedOrders.clear();
      ui.modal = null;
      saveState();
      showToast('发货信息已更新');
    }
    if (form.dataset.form === 'ozon-bulk') {
      const credentialRows = parseBulkOzonCredentials(data.stores);
      if (!credentialRows.length) return showToast('请至少填写一行：店铺名称,Client ID,API Key');
      ui.scope = 'all';
      ui.tab = 'stores';
      ui.modal = null;
      saveState();
      try {
        await createOperationTask(
          '/api/ozon/bind-bulk-task',
          { stores: credentialRows, validateWithOzon: false, autoSyncProducts: data.autoSyncProducts === 'on' },
          `批量绑定任务已创建`
        );
      } catch (error) {
        showToast(error.message || '批量绑定失败');
      }
    }
    if (form.dataset.form === '1688-import') {
      const urls = parse1688Urls(data.urls);
      if (!urls.length) return showToast('请填写有效的 1688 商品链接');
      try {
        const response = await fetch(`${API_BASE_URL}/api/1688/import-url`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ urls })
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.error || '1688 采集失败');
        state = add1688Sources(state, result.sources || []);
      } catch (error) {
        state = add1688Sources(state, urls.map((url) => {
          const offerId = extract1688OfferId(url);
          return {
            url,
            offerId,
            title: `1688 商品 ${offerId}`,
            priceMin: 10,
            priceMax: 10,
            status: 'parsed',
            error: '后端不可用，已按链接创建待复核来源'
          };
        }));
      }
      ui.tab = 'import';
      ui.modal = null;
      saveState();
      showToast(`已导入 ${urls.length} 个 1688 链接`);
    }
    if (form.dataset.form === 'publish') {
      const formData = new FormData(form);
      const productIds = formData.getAll('productIds');
      const storeIds = formData.getAll('storeIds');
      if (!productIds.length || !storeIds.length) return showToast('请选择商品和店铺');
      try {
        const response = await fetch(`${API_BASE_URL}/api/products/publish`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ productIds, storeIds })
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.error || '批量发布失败');
        const published = (result.results || []).map((item) => {
          const product = state.products.find((candidate) => candidate.id === item.productId) || {};
          return {
            id: `${item.storeId}-${item.offerId}`,
            storeId: item.storeId,
            productId: item.productId,
            offerId: item.offerId,
            sourceUrl: product.sourceUrl || '',
            status: item.status,
            importTaskId: item.importTaskId || '',
            error: item.error || '',
            priceCny: product.suggestedPriceCny || product.suggestedPriceRub || product.price,
            priceRub: product.suggestedPriceCny || product.suggestedPriceRub || product.price,
            stock: product.stock || 0,
            createdAt: state.today || TODAY
          };
        });
        state.publishedProducts = [
          ...(state.publishedProducts || []),
          ...published.filter((item) => !(state.publishedProducts || []).some((existing) => existing.storeId === item.storeId && existing.offerId === item.offerId))
        ];
      } catch (error) {
        state = publishProductsToStores(state, productIds, storeIds);
      }
      ui.tab = 'published';
      ui.publishedPage = 1;
      ui.modal = null;
      saveState();
      await refreshPublishJobs(false, true);
      showToast('上架任务已创建，可在上架记录查看状态');
    }
    if (form.dataset.form === 'price') {
      const priceCny = Number(data.priceCny);
      if (!priceCny || priceCny <= 0) return showToast('请填写大于 0 的价格');
      const payload = { priceCny };
      if (data.oldPriceCny) payload.oldPriceCny = Number(data.oldPriceCny);
      if (data.minPriceCny) payload.minPriceCny = Number(data.minPriceCny);
      try {
        const response = await fetch(`${API_BASE_URL}/api/stores/${ui.modal.storeId}/products/${encodeURIComponent(ui.modal.offerId)}/price`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.error || '改价失败');
        state = updatePublishedProductPrice(state, ui.modal.storeId, ui.modal.offerId, result.product.priceCny ?? result.product.priceRub);
        ui.modal = null;
        saveState();
        showToast('价格已更新');
      } catch (error) {
        showToast(error.message || '改价失败');
      }
    }
    if (form.dataset.form === 'inventory') {
      state = adjustInventory(state, Array.from(ui.selectedProducts), data.mode, Number(data.value));
      ui.selectedProducts.clear();
      ui.modal = null;
      saveState();
      showToast('库存已批量修改');
    }
    if (form.dataset.form === 'promotion') {
      const productIds = state.products.filter((product) => product.storeId === data.storeId).map((product) => product.id);
      state = addPromotion(state, { ...data, productIds });
      ui.tab = 'promotions';
      ui.modal = null;
      saveState();
      showToast('促销活动已创建');
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    render();
    refreshBoundStores();
    refreshTasks(true);
  });
  document.addEventListener('click', handleClick);
  document.addEventListener('change', handleChange);
  document.addEventListener('input', handleInput);
  document.addEventListener('submit', handleSubmit);

  return api;
});
