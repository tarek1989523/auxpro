#property copyright "Gold Trading Bot"
#property version   "1.00"
#property strict

input string   ServerURL = "http://YOUR_SERVER_IP:9999";
input double   LotSize   = 0.01;
input int      Slippage  = 10;
input int      Magic     = 202608;

string signal_url;
int last_id = 0;
datetime last_bar = 0;

int OnInit() {
   signal_url = ServerURL + "/signal";
   if (StringFind(ServerURL, "127.0.0.1") >= 0 || StringFind(ServerURL, "localhost") >= 0)
      Print("WARNING: Using localhost. EA must be on the same PC as the bot!");
   else
      Print("Signal server: ", ServerURL);
   return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason) {}

void OnTick() {
   if (Time[0] == last_bar) return;
   last_bar = Time[0];
   CheckSignal();
}

void CheckSignal() {
   string headers;
   char data[], result[];
   string method = "GET";

   int res = WebRequest(method, signal_url, "", 5000, data, result, headers);
   if (res == -1) {
      int err = GetLastError();
      if (err != 0) Print("WebRequest error: ", err, " - Add ", signal_url, " to Tools > Options > Expert Advisors > Allowed URLs");
      return;
   }

   string json = CharArrayToString(result);
   int id = GetJSONInt(json, "id");
   if (id <= last_id) return;

   last_id = id;
   string sig_type = GetJSONString(json, "type");
   double lot = GetJSONDouble(json, "lot");
   double price = GetJSONDouble(json, "price");
   double sl = GetJSONDouble(json, "sl");
   double tp = GetJSONDouble(json, "tp");

   if (sig_type == "") return;
   if (lot <= 0) lot = LotSize;

   for (int i = OrdersTotal() - 1; i >= 0; i--) {
      if (OrderSelect(i, SELECT_BY_POS, MODE_TRADES)) {
         if (OrderMagicNumber() == Magic && OrderSymbol() == _Symbol) {
            string pos_type = (OrderType() == OP_BUY) ? "BUY" : "SELL";
            if (pos_type == sig_type) {
               Print("Signal #", id, " ", sig_type, " - already in position. Skipping.");
               return;
            }
         }
      }
   }

   int cmd = (sig_type == "BUY") ? OP_BUY : OP_SELL;
   double exec_price = (sig_type == "BUY") ? Ask : Bid;
   int ticket = OrderSend(_Symbol, cmd, lot, exec_price, Slippage, sl, tp, "Signal", Magic, 0, clrNONE);

   if (ticket > 0) {
      Print("Signal #", id, " ", sig_type, " @ ", exec_price, " SL:", sl, " TP:", tp, " Ticket:", ticket);
   } else {
      Print("Signal #", id, " FAILED: ", GetLastError());
   }
}

string GetJSONString(string json, string key) {
   string search = "\"" + key + "\":\"";
   int pos = StringFind(json, search);
   if (pos < 0) return "";
   pos += StringLen(search);
   int end = StringFind(json, "\"", pos);
   if (end < 0) return "";
   return StringSubstr(json, pos, end - pos);
}

double GetJSONDouble(string json, string key) {
   string search = "\"" + key + "\":";
   int pos = StringFind(json, search);
   if (pos < 0) return 0;
   pos += StringLen(search);
   int end = StringFind(json, ",", pos);
   if (end < 0) end = StringFind(json, "}", pos);
   if (end < 0) return 0;
   string val = StringSubstr(json, pos, end - pos);
   return StringToDouble(val);
}

int GetJSONInt(string json, string key) {
   string search = "\"" + key + "\":";
   int pos = StringFind(json, search);
   if (pos < 0) return 0;
   pos += StringLen(search);
   int end = StringFind(json, ",", pos);
   if (end < 0) end = StringFind(json, "}", pos);
   if (end < 0) return 0;
   string val = StringSubstr(json, pos, end - pos);
   return (int)StringToInteger(val);
}
