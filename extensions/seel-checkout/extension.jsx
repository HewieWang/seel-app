import { reactExtension, useApi, BlockStack, Checkbox, Text, Banner } from '@shopify/ui-extensions-react/checkout';
import { useEffect, useState } from 'react';

export default reactExtension('checkout.order-summary.render-after', () => <Extension />);

function Extension() {
  const { buyerIdentity, extension } = useApi();
  const [quote, setQuote] = useState(null);
  const [optedIn, setOptedIn] = useState(false);

  useEffect(() => {
    fetch('/apps/seel-proxy/quote', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        cart: { /* 可以从 useApi 获取实际数据，这里简化 */ },
        customer: {
          id: buyerIdentity?.customer?.id,
          tags: buyerIdentity?.customer?.tags,
          order_count: buyerIdentity?.customer?.numberOfOrders
        }
      })
    })
      .then(res => res.json())
      .then(data => {
        setQuote(data.quote);
        if (data.promotion_type === 'membership_free') setOptedIn(true);
      });
  }, []);

  const handleChange = (checked) => {
    setOptedIn(checked);
    extension.settings?.set('seel_quote_id', checked ? quote.quote_id : null);
  };

  if (!quote) return null;

  const isFree = quote.premium_amount === 0;

  return (
    <Banner status="info">
      <BlockStack>
        <Checkbox name="seel" checked={optedIn} onChange={handleChange}>
          {isFree ? '会员免费保险' : `添加保险 +${quote.premium_amount}`}
        </Checkbox>
      </BlockStack>
    </Banner>
  );
}
