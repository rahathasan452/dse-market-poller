import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

// Supabase Environment Variables
const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const TELEGRAM_BOT_TOKEN = Deno.env.get("TELEGRAM_BOT_TOKEN")!;

const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY);

// Send plain Markdown message
async function sendMessage(chatId: number | string, text: string, replyMarkup?: any) {
  if (!TELEGRAM_BOT_TOKEN) return;
  await fetch(`https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      chat_id: chatId,
      text: text,
      parse_mode: "Markdown",
      reply_markup: replyMarkup,
    }),
  });
}

// Answer Telegram Inline Query (Autofill suggestions while typing @bot_name)
async function answerInlineQuery(inlineQueryId: string, results: any[]) {
  if (!TELEGRAM_BOT_TOKEN) return;
  await fetch(`https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/answerInlineQuery`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      inline_query_id: inlineQueryId,
      results: results,
      cache_time: 300,
    }),
  });
}

// Search Supabase for matching ticker suggestions
async function searchTickers(queryStr: string): Promise<string[]> {
  const clean = queryStr.trim().toUpperCase();
  if (!clean) return [];

  const { data } = await supabase
    .from("dse_market_snapshots")
    .select("ticker")
    .ilike("ticker", `%${clean}%`)
    .limit(10);

  if (!data) return [];

  const unique = Array.from(new Set(data.map((r: any) => r.ticker)));
  return unique.slice(0, 5);
}

Deno.serve(async (req: Request) => {
  try {
    if (req.method !== "POST") {
      return new Response("Telegram Webhook Endpoint OK", { status: 200 });
    }

    const payload = await req.json();

    // 1. Handle Inline Query Autofill (@bot_name TICKER)
    if (payload.inline_query) {
      const iq = payload.inline_query;
      const query = iq.query || "";
      const matches = await searchTickers(query);

      const results = matches.map((ticker, index) => ({
        type: "article",
        id: `${index}_${ticker}`,
        title: ticker,
        description: `Check price or set alert for ${ticker}`,
        input_message_content: {
          message_text: `/price ${ticker}`,
        },
      }));

      await answerInlineQuery(iq.id, results);
      return new Response("OK", { status: 200 });
    }

    // 2. Handle Button Callbacks
    if (payload.callback_query) {
      const cb = payload.callback_query;
      const chatId = cb.message.chat.id;
      const dataStr = cb.data;

      if (dataStr.startsWith("PRICE_")) {
        const ticker = dataStr.replace("PRICE_", "");
        await fetchPriceAndReply(chatId, ticker);
      } else if (dataStr.startsWith("ADD_")) {
        const parts = dataStr.split("_");
        const ticker = parts[1];
        const val1 = parseFloat(parts[2]);
        const val2 = parts[3] ? parseFloat(parts[3]) : NaN;
        await processAddAlertCommand(chatId, ticker, val1, val2);
      }

      return new Response("OK", { status: 200 });
    }

    const message = payload.message;
    if (!message || !message.text || !message.chat) {
      return new Response("No message to process", { status: 200 });
    }

    const chatId = message.chat.id;
    const rawText: string = message.text.trim();
    const parts = rawText.split(/\s+/);
    const command = parts[0].toLowerCase();

    // Command: /start or /help
    if (command === "/start" || command === "/help") {
      const helpMsg = 
`🤖 *DSE Stock Price Alert Bot*

Available Commands:

🎯 *Single or Dual Alert (Take Profit & Stop Loss in 1 Command):*
  🔹 \`/add GP 280 240\`
     _(Sets Take Profit ABOVE 280 & Stop Loss BELOW 240 in one go!)_
  🔹 \`/add GP 280 ABOVE\`
     _(Single alert when price hits 280)_

📋 *Manage Alerts:*
  🔹 \`/list\` — View all your active alerts
  🔹 \`/del 4 5 6\` — Delete multiple alerts by ID
  🔹 \`/del GP\` — Delete all alerts for ticker GP
  🔹 \`/del all\` — Delete all active alerts

📊 *Market Quotes:*
  🔹 \`/price <TICKER>\` — Check live stock price (e.g. \`/price GP\`)`;

      await sendMessage(chatId, helpMsg);
      return new Response("OK", { status: 200 });
    }

    // Command: /add TICKER PRICE1 [PRICE2 or CONDITION]
    if (command === "/add" || command === "/alert") {
      if (parts.length < 3) {
        await sendMessage(
          chatId, 
          "⚠️ *Invalid Format!*\n\n" +
          "• *Dual Target (Take Profit + Stop Loss):*\n`/add GP 280 240`\n\n" +
          "• *Single Target:*\n`/add GP 280 ABOVE`"
        );
        return new Response("OK", { status: 200 });
      }

      const inputTicker = parts[1].toUpperCase();
      const val1 = parseFloat(parts[2]);
      
      let val2 = NaN;
      let explicitCondition = "";

      if (parts.length >= 4) {
        const p4 = parts[3].toUpperCase();
        if (p4 === "ABOVE" || p4 === "BELOW") {
          explicitCondition = p4;
        } else {
          val2 = parseFloat(p4);
        }
      }

      if (isNaN(val1)) {
        await sendMessage(chatId, "⚠️ *Invalid Price!* Price must be a number.\nExample: `/add GP 280 240`");
        return new Response("OK", { status: 200 });
      }

      // Check if ticker exists
      const { data: exactMatch } = await supabase
        .from("dse_market_snapshots")
        .select("ticker")
        .eq("ticker", inputTicker)
        .limit(1);

      if (!exactMatch || exactMatch.length === 0) {
        const suggestions = await searchTickers(inputTicker);
        if (suggestions.length > 0) {
          const val2Param = isNaN(val2) ? "" : `_${val2}`;
          const buttons = suggestions.map((s) => [
            { text: `➕ Set alert for ${s}`, callback_data: `ADD_${s}_${val1}${val2Param}` },
          ]);
          await sendMessage(
            chatId,
            `🔍 Ticker \`${inputTicker}\` not found.\nDid you mean one of these? Tap below:`,
            { inline_keyboard: buttons }
          );
          return new Response("OK", { status: 200 });
        }
      }

      if (!isNaN(val2)) {
        await processAddAlertCommand(chatId, inputTicker, val1, val2);
      } else {
        const condition = explicitCondition || "ABOVE";
        await processAddAlertCommand(chatId, inputTicker, val1, NaN, condition);
      }

      return new Response("OK", { status: 200 });
    }

    // Command: /list
    if (command === "/list") {
      const { data: alerts, error } = await supabase
        .from("price_alerts")
        .select("*")
        .eq("recipient", chatId.toString())
        .eq("is_active", true)
        .order("id", { ascending: true });

      if (error) {
        await sendMessage(chatId, `❌ Error fetching alerts: ${error.message}`);
        return new Response("OK", { status: 200 });
      }

      if (!alerts || alerts.length === 0) {
        await sendMessage(chatId, "ℹ️ You have no active price alerts.\nUse `/add TICKER PRICE` to create one!");
        return new Response("OK", { status: 200 });
      }

      let listMsg = "📋 *Your Active Price Alerts:*\n\n";
      alerts.forEach((alert: any) => {
        const symbol = alert.condition === "ABOVE" ? "📈" : "📉";
        const label = alert.condition === "ABOVE" ? "Take Profit" : "Stop Loss";
        listMsg += `🆔 \`#${alert.id}\` | *${alert.ticker}* ${symbol} ${label} (${alert.condition}) *${alert.target_price} BDT*\n`;
      });
      listMsg += "\nDelete alerts:\n• `/del 4 5` (Multiple IDs)\n• `/del GP` (By Ticker)\n• `/del all` (Delete All)";

      await sendMessage(chatId, listMsg);
      return new Response("OK", { status: 200 });
    }

    // Command: /del ALERT_ID(S) or TICKER or ALL
    if (command === "/del" || command === "/delete" || command === "/remove") {
      if (parts.length < 2) {
        await sendMessage(
          chatId, 
          "⚠️ *Invalid Format!*\n\n" +
          "• *Multiple IDs:* `/del 4 5 6`\n" +
          "• *By Ticker:* `/del GP`\n" +
          "• *Delete All:* `/del all`"
        );
        return new Response("OK", { status: 200 });
      }

      const args = parts.slice(1);

      if (args.length === 1 && args[0].toLowerCase() === "all") {
        const { data, error } = await supabase
          .from("price_alerts")
          .update({ is_active: false })
          .eq("recipient", chatId.toString())
          .eq("is_active", true)
          .select();

        if (error) {
          await sendMessage(chatId, `❌ Error deleting alerts: ${error.message}`);
        } else if (!data || data.length === 0) {
          await sendMessage(chatId, "ℹ️ You have no active alerts to delete.");
        } else {
          await sendMessage(chatId, `🗑️ *Removed all ${data.length} active price alert(s).*`);
        }
        return new Response("OK", { status: 200 });
      }

      const idList: number[] = [];
      const nonNumeric: string[] = [];

      args.forEach((arg) => {
        arg.split(",").forEach((item) => {
          const clean = item.trim();
          const id = parseInt(clean, 10);
          if (!isNaN(id)) {
            idList.push(id);
          } else if (clean) {
            nonNumeric.push(clean.toUpperCase());
          }
        });
      });

      if (idList.length > 0) {
        const { data, error } = await supabase
          .from("price_alerts")
          .update({ is_active: false })
          .in("id", idList)
          .eq("recipient", chatId.toString())
          .eq("is_active", true)
          .select();

        if (error) {
          await sendMessage(chatId, `❌ Error deleting alerts: ${error.message}`);
        } else if (!data || data.length === 0) {
          await sendMessage(chatId, `⚠️ No active alerts found with IDs: \`${idList.join(", ")}\`.`);
        } else {
          const deletedItems = data.map((d: any) => `#${d.id} (${d.ticker})`).join(", ");
          await sendMessage(chatId, `🗑️ *Deleted ${data.length} alert(s):* ${deletedItems}`);
        }
        return new Response("OK", { status: 200 });
      }

      if (nonNumeric.length > 0) {
        const ticker = nonNumeric[0];
        const { data, error } = await supabase
          .from("price_alerts")
          .update({ is_active: false })
          .eq("ticker", ticker)
          .eq("recipient", chatId.toString())
          .eq("is_active", true)
          .select();

        if (error) {
          await sendMessage(chatId, `❌ Error deleting alerts for ${ticker}: ${error.message}`);
        } else if (!data || data.length === 0) {
          await sendMessage(chatId, `⚠️ No active alerts found for ticker \`${ticker}\`.`);
        } else {
          await sendMessage(chatId, `🗑️ *Removed ${data.length} active alert(s) for ticker \`${ticker}\`.*`);
        }
        return new Response("OK", { status: 200 });
      }
    }

    // Command: /price TICKER
    if (command === "/price" || command === "/quote") {
      if (parts.length < 2) {
        await sendMessage(chatId, "⚠️ *Invalid Format!*\nUse: `/price <TICKER>`\nExample: `/price GP`");
        return new Response("OK", { status: 200 });
      }

      const inputTicker = parts[1].toUpperCase();
      await fetchPriceAndReply(chatId, inputTicker);
      return new Response("OK", { status: 200 });
    }

    await sendMessage(chatId, "❓ Unknown command. Type `/help` to view available commands.");
    return new Response("OK", { status: 200 });

  } catch (err: any) {
    console.error("Webhook Error:", err);
    return new Response(JSON.stringify({ error: err.message }), { status: 500 });
  }
});

// Helper: Process single or dual alert commands with Instant Evaluation
async function processAddAlertCommand(
  chatId: number | string, 
  ticker: string, 
  val1: number, 
  val2: number = NaN, 
  explicitCondition: string = "ABOVE"
) {
  // Fetch current price snapshot to check if target is ALREADY met!
  const { data: priceData } = await supabase
    .from("dse_market_snapshots")
    .select("close, date")
    .eq("ticker", ticker)
    .order("date", { ascending: false })
    .limit(1);

  const currentPrice = priceData && priceData.length > 0 ? parseFloat(priceData[0].close) : null;

  // Case 1: Dual Bracket Alert
  if (!isNaN(val2)) {
    const highPrice = Math.max(val1, val2); // Take Profit (ABOVE)
    const lowPrice = Math.min(val1, val2);  // Stop Loss (BELOW)

    const tpTriggered = currentPrice !== null && currentPrice >= highPrice;
    const slTriggered = currentPrice !== null && currentPrice <= lowPrice;

    // Insert Take Profit
    const { data: tpData } = await supabase.from("price_alerts").insert({
      ticker: ticker,
      target_price: highPrice,
      condition: "ABOVE",
      recipient: chatId.toString(),
      is_active: !tpTriggered,
      last_triggered_at: tpTriggered ? new Date().toISOString() : null
    }).select().single();

    // Insert Stop Loss
    const { data: slData } = await supabase.from("price_alerts").insert({
      ticker: ticker,
      target_price: lowPrice,
      condition: "BELOW",
      recipient: chatId.toString(),
      is_active: !slTriggered,
      last_triggered_at: slTriggered ? new Date().toISOString() : null
    }).select().single();

    let msg = `🎯 *Dual Bracket Alert Configured for ${ticker}!*\n\n`;
    msg += `📈 *Take Profit (ABOVE ${highPrice} BDT):* ${tpTriggered ? "🚨 *TRIGGERED IMMEDIATELY!*" : `Active (ID: \`#${tpData?.id}\`)`}\n`;
    msg += `📉 *Stop Loss (BELOW ${lowPrice} BDT):* ${slTriggered ? "🚨 *TRIGGERED IMMEDIATELY!*" : `Active (ID: \`#${slData?.id}\`)`}\n\n`;
    if (currentPrice !== null) {
      msg += `💰 *Current Price:* *${currentPrice} BDT*`;
    }

    await sendMessage(chatId, msg);
    return;
  }

  // Case 2: Single Alert
  const isTriggeredNow = currentPrice !== null && (
    (explicitCondition === "ABOVE" && currentPrice >= val1) ||
    (explicitCondition === "BELOW" && currentPrice <= val1)
  );

  const { data, error } = await supabase.from("price_alerts").insert({
    ticker: ticker,
    target_price: val1,
    condition: explicitCondition,
    recipient: chatId.toString(),
    is_active: !isTriggeredNow,
    last_triggered_at: isTriggeredNow ? new Date().toISOString() : null
  }).select().single();

  if (error) {
    await sendMessage(chatId, `❌ *Failed to create alert:* ${error.message}`);
  } else {
    const symbol = explicitCondition === "ABOVE" ? "📈" : "📉";
    const label = explicitCondition === "ABOVE" ? "Take Profit" : "Stop Loss";

    if (isTriggeredNow) {
      const instantMsg = 
`🚨 *INSTANT PRICE ALERT TRIGGERED!* ${symbol}

📌 *Stock:* \`${ticker}\`
💰 *Current Price:* *${currentPrice} BDT*
🎯 *Target (${label}):* *${val1} BDT* (${explicitCondition})

_The current market price already satisfies your target!_`;
      await sendMessage(chatId, instantMsg);
    } else {
      await sendMessage(
        chatId, 
        `✅ *Alert Created!* ${symbol}\n\n📌 *Stock:* \`${ticker}\`\n🎯 *${label}:* *${val1} BDT* (${explicitCondition})\n🆔 *Alert ID:* \`#${data.id}\`\n💰 *Current Price:* *${currentPrice ?? "-"} BDT*`
      );
    }
  }
}

// Helper: Fetch price and reply
async function fetchPriceAndReply(chatId: number | string, ticker: string) {
  const { data: priceData } = await supabase
    .from("dse_market_snapshots")
    .select("ticker, close, open, high, low, volume, date")
    .eq("ticker", ticker)
    .order("date", { ascending: false })
    .limit(1);

  if (!priceData || priceData.length === 0) {
    const suggestions = await searchTickers(ticker);
    if (suggestions.length > 0) {
      const buttons = suggestions.map((s) => [
        { text: `📊 View ${s} Price`, callback_data: `PRICE_${s}` },
      ]);
      await sendMessage(
        chatId,
        `🔍 Ticker \`${ticker}\` not found.\nDid you mean one of these? Tap below:`,
        { inline_keyboard: buttons }
      );
    } else {
      await sendMessage(chatId, `⚠️ No price data found for ticker \`${ticker}\`.`);
    }
  } else {
    const row = priceData[0];
    const quoteMsg = 
`📊 *Latest Quote: ${row.ticker}*

💰 *Close Price:* *${row.close} BDT*
📈 *High / Low:* ${row.high || "-"} / ${row.low || "-"} BDT
📦 *Volume:* ${row.volume ? row.volume.toLocaleString() : "-"}
📅 *Date:* ${row.date}`;

    await sendMessage(chatId, quoteMsg);
  }
}
