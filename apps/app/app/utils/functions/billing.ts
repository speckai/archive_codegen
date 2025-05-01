export async function getIsSubscribed(token: string): Promise<boolean> {
  try {
    const response = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL}/account/billing/is_subscribed`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      },
    );

    if (!response.ok) {
      throw new Error("Failed to check subscription status");
    }

    const data = await response.json();
    return data.is_subscribed;
  } catch (error) {
    console.error("Error checking subscription status:", error);
    return false;
  }
}

export interface SubscriptionDetails {
  subscriptionFound: boolean;
  subscriptionLink?: string;
  manageLink?: string;
  monthlyAmount?: number;
  nextBillingDate?: number;
  daysSubscribed?: number;
  currency?: string;
}

export async function getSubscriptionData(
  token: string,
): Promise<SubscriptionDetails> {
  try {
    const response = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL}/account/billing/details`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      },
    );

    if (!response.ok) {
      throw new Error("Failed to fetch subscription details");
    }

    const data = await response.json();
    return {
      subscriptionFound: data.subscription_found,
      subscriptionLink: data.subscription_link,
      manageLink: data.manage_link,
      monthlyAmount: data.monthly_amount,
      nextBillingDate: data.next_billing_date,
      daysSubscribed: data.days_subscribed,
      currency: data.currency,
    };
  } catch (error) {
    console.error("Error fetching subscription details:", error);
    return { subscriptionFound: false };
  }
}
