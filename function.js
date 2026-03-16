// 文件名: run.js
// npx shopify app function build

export function run(input) {
  const cart = input.cart;
  const quoteId = cart.metafield?.find(m => m.key === 'seel_quote_id')?.value;
  const premium = cart.metafield?.find(m => m.key === 'seel_premium')?.value;

  if (!quoteId) return { operations: [] };

  const operations = [{
    addCustomOrderLineItem: {
      title: premium === '0' ? '免费保险' : 'Seel保险',
      quantity: 1,
      originalUnitPrice: premium || '0',
      discountedUnitPrice: premium || '0',
      requiresShipping: false,
      attributes: [{ key: 'seel_quote_id', value: quoteId }]
    }
  }];

  return { operations };
}
