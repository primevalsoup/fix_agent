# FIX Protocol Message Examples

This document shows examples of actual FIX messages from the test runs, with tag breakdowns.

## Message Type Reference

- **MsgType=A**: Logon
- **MsgType=D**: NewOrderSingle
- **MsgType=8**: ExecutionReport
- **MsgType=F**: OrderCancelRequest
- **MsgType=G**: OrderCancelReplaceRequest (Amend)
- **MsgType=9**: OrderCancelReject

## 1. Logon (MsgType=A)

### RECV: Client → Broker
```
8=FIX.4.2|9=72|35=A|49=TEST_CLIENT|56=BROKER|34=1|52=20251023-02:20:57.533|98=0|108=30|10=026|
```

**Tag Breakdown:**
- `8=FIX.4.2` - BeginString (protocol version)
- `9=72` - BodyLength
- `35=A` - MsgType: Logon
- `49=TEST_CLIENT` - SenderCompID
- `56=BROKER` - TargetCompID
- `34=1` - MsgSeqNum
- `52=20251023-02:20:57.533` - SendingTime
- `98=0` - EncryptMethod (None)
- `108=30` - HeartBtInt (30 seconds)
- `10=026` - CheckSum

### SEND: Broker → Client
```
8=FIX.4.2|9=72|35=A|49=BROKER|56=TEST_CLIENT|34=1|98=0|108=30|52=20251023-02:20:57.535|10=028|
```

**Tag Breakdown:**
- Same structure as above, with sender/target reversed

---

## 2. NewOrderSingle (MsgType=D)

### RECV: Client → Broker
```
8=FIX.4.2|9=137|35=D|49=TEST_CLIENT|56=BROKER|34=2|52=20251023-02:20:57.636|11=EXEC_TEST_001|21=1|55=AAPL|54=1|60=20251023-02:20:57.636|40=1|38=100|59=0|10=185|
```

**Tag Breakdown:**
- `35=D` - MsgType: NewOrderSingle
- `11=EXEC_TEST_001` - ClOrdID (Client Order ID)
- `21=1` - HandlInst (Automated execution)
- `55=AAPL` - Symbol
- `54=1` - Side: Buy (1=Buy, 2=Sell)
- `60=20251023-02:20:57.636` - TransactTime
- `40=1` - OrdType: Market (1=Market, 2=Limit)
- `38=100` - OrderQty (100 shares)
- `59=0` - TimeInForce: Day (0=Day)

---

## 3. ExecutionReport - New Order (MsgType=8, ExecType=0)

### SEND: Broker → Client
```
8=FIX.4.2|9=142|35=8|49=BROKER|56=TEST_CLIENT|34=2|11=EXEC_TEST_001|17=3511e8fe|150=0|39=0|55=AAPL|54=1|38=100|40=1|14=0|6=0|151=100|52=20251023-02:20:57.662|10=188|
```

**Tag Breakdown:**
- `35=8` - MsgType: ExecutionReport
- `11=EXEC_TEST_001` - ClOrdID
- `17=3511e8fe` - ExecID (Execution ID)
- `150=0` - ExecType: New (0=New, 1=PartialFill, 2=Fill, 4=Canceled, 5=Replaced)
- `39=0` - OrdStatus: New (0=New, 1=PartiallyFilled, 2=Filled, 4=Canceled)
- `55=AAPL` - Symbol
- `54=1` - Side: Buy
- `38=100` - OrderQty
- `40=1` - OrdType: Market
- `14=0` - CumQty (Cumulative filled quantity)
- `6=0` - AvgPx (Average price)
- `151=100` - LeavesQty (Remaining quantity)

---

## 4. ExecutionReport - Filled (MsgType=8, ExecType=2)

### SEND: Broker → Client
```
8=FIX.4.2|9=162|35=8|49=BROKER|56=TEST_CLIENT|34=3|11=EXEC_TEST_001|17=62a10176|150=2|39=2|55=AAPL|54=1|38=100|40=1|32=100|31=230.1|14=100|6=230.1|151=0|52=20251023-02:20:57.891|10=235|
```

**Tag Breakdown:**
- `150=2` - ExecType: Fill (order completely filled)
- `39=2` - OrdStatus: Filled
- `32=100` - LastQty (Quantity of this fill)
- `31=230.1` - LastPx (Price of this fill)
- `14=100` - CumQty (Total filled: 100)
- `6=230.1` - AvgPx (Average fill price)
- `151=0` - LeavesQty (Nothing remaining)

---

## 5. ExecutionReport - Partial Fill (MsgType=8, ExecType=1)

### SEND: Broker → Client
```
8=FIX.4.2|9=164|35=8|49=BROKER|56=TEST_CLIENT|34=6|11=PARTIAL_TEST_001|17=5052fabb|150=1|39=1|55=MSFT|54=2|38=100|40=2|32=50|31=420.0|14=50|6=420.0|151=50|52=20251023-02:20:58.240|10=085|
```

**Tag Breakdown:**
- `150=1` - ExecType: PartialFill
- `39=1` - OrdStatus: PartiallyFilled
- `32=50` - LastQty (This fill: 50 shares)
- `31=420.0` - LastPx (Fill price: $420.00)
- `14=50` - CumQty (Total filled so far: 50)
- `6=420.0` - AvgPx (Average price: $420.00)
- `151=50` - LeavesQty (Remaining: 50 shares)

---

## 6. Multiple Partial Fills Example

Order for 100 shares of GOOGL filled in three parts: 30 + 40 + 30

### First Partial Fill (30 shares)
```
8=FIX.4.2|9=168|35=8|49=BROKER|56=TEST_CLIENT|34=9|11=MULTI_PARTIAL_001|17=f47fedbb|150=1|39=1|55=GOOGL|54=1|38=100|40=1|32=30|31=167.25|14=30|6=167.25|151=70|52=20251023-02:20:58.594|10=216|
```
- `32=30` - LastQty: 30 shares
- `14=30` - CumQty: 30 total
- `151=70` - LeavesQty: 70 remaining

### Second Partial Fill (40 shares)
```
8=FIX.4.2|9=169|35=8|49=BROKER|56=TEST_CLIENT|34=10|11=MULTI_PARTIAL_001|17=c3308d4b|150=1|39=1|55=GOOGL|54=1|38=100|40=1|32=40|31=167.25|14=70|6=167.25|151=30|52=20251023-02:20:58.709|10=103|
```
- `32=40` - LastQty: 40 shares
- `14=70` - CumQty: 70 total (30+40)
- `151=30` - LeavesQty: 30 remaining

### Final Fill (30 shares)
```
8=FIX.4.2|9=169|35=8|49=BROKER|56=TEST_CLIENT|34=11|11=MULTI_PARTIAL_001|17=a4954d77|150=2|39=2|55=GOOGL|54=1|38=100|40=1|32=30|31=167.25|14=100|6=167.25|151=0|52=20251023-02:20:58.825|10=061|
```
- `150=2` - ExecType: Fill (complete)
- `39=2` - OrdStatus: Filled
- `32=30` - LastQty: 30 shares
- `14=100` - CumQty: 100 total (30+40+30)
- `151=0` - LeavesQty: 0 (complete)

---

## 7. OrderCancelRequest (MsgType=F)

### RECV: Client → Broker
```
8=FIX.4.2|9=145|35=F|49=TEST_CLIENT|56=BROKER|34=3|52=20251023-02:20:59.854|41=LIMIT_CANCEL_001|11=CANCEL_LIMIT_CANCEL_001|55=AAPL|54=1|60=20251023-02:20:59.854|10=228|
```

**Tag Breakdown:**
- `35=F` - MsgType: OrderCancelRequest
- `41=LIMIT_CANCEL_001` - OrigClOrdID (Original Client Order ID to cancel)
- `11=CANCEL_LIMIT_CANCEL_001` - ClOrdID (New ID for this cancel request)
- `55=AAPL` - Symbol
- `54=1` - Side: Buy

### SEND: ExecutionReport - Canceled (ExecType=4)
```
8=FIX.4.2|9=160|35=8|49=BROKER|56=TEST_CLIENT|34=21|11=CANCEL_LIMIT_CANCEL_001|17=dc6c0ed9|150=4|39=4|41=LIMIT_CANCEL_001|55=AAPL|54=1|38=100|40=2|14=0|6=0|151=0|52=20251023-02:20:59.859|10=093|
```

**Tag Breakdown:**
- `35=8` - MsgType: ExecutionReport
- `11=CANCEL_LIMIT_CANCEL_001` - ClOrdID (cancel request ID)
- `150=4` - ExecType: Canceled
- `39=4` - OrdStatus: Canceled
- `41=LIMIT_CANCEL_001` - OrigClOrdID (original order that was canceled)
- `151=0` - LeavesQty: 0 (nothing remaining)

---

## 8. OrderCancelReject (MsgType=9)

### Example 1: Order Not Found

#### RECV: Client tries to cancel non-existent order
```
8=FIX.4.2|9=147|35=F|49=TEST_CLIENT|56=BROKER|34=2|52=20251023-02:21:00.579|41=NONEXISTENT_ORDER|11=CANCEL_NONEXISTENT_ORDER|55=AAPL|54=1|60=20251023-02:21:00.579|10=095|
```

#### SEND: OrderCancelReject
```
8=FIX.4.2|9=140|35=9|49=BROKER|56=TEST_CLIENT|34=25|11=CANCEL_NONEXISTENT_ORDER|41=NONEXISTENT_ORDER|39=0|434=1|58=Order not found|52=20251023-02:21:00.585|10=075|
```

**Tag Breakdown:**
- `35=9` - MsgType: OrderCancelReject
- `11=CANCEL_NONEXISTENT_ORDER` - ClOrdID (cancel request ID)
- `41=NONEXISTENT_ORDER` - OrigClOrdID (order that was requested to cancel)
- `39=0` - OrdStatus
- `434=1` - CxlRejReason: 1=Unknown order (0=Too late, 1=Unknown order)
- `58=Order not found` - Text (human-readable reason)

### Example 2: Too Late to Cancel (Already Filled)

#### RECV: Client tries to cancel filled order
```
8=FIX.4.2|9=148|35=F|49=TEST_CLIENT|56=BROKER|34=3|52=20251023-02:21:01.034|41=FILLED_CANCEL_001|11=CANCEL_FILLED_CANCEL_001|55=GOOGL|54=1|60=20251023-02:21:01.034|10=119|
```

#### SEND: OrderCancelReject
```
8=FIX.4.2|9=145|35=9|49=BROKER|56=TEST_CLIENT|34=28|11=CANCEL_FILLED_CANCEL_001|41=FILLED_CANCEL_001|39=0|434=0|58=Order already FILLED|52=20251023-02:21:01.040|10=064|
```

**Tag Breakdown:**
- `434=0` - CxlRejReason: 0=Too late to cancel
- `58=Order already FILLED` - Text

---

## 9. OrderCancelReplaceRequest - Amend (MsgType=G)

### Example 1: Amend Quantity

#### RECV: Client amends quantity from 100 to 150
```
8=FIX.4.2|9=161|35=G|49=TEST_CLIENT|56=BROKER|34=3|52=20251023-02:21:01.369|41=AMEND_QTY_001|11=AMEND_QTY_001_V2|21=1|55=AAPL|54=1|60=20251023-02:21:01.369|40=2|44=225.0|38=150|10=173|
```

**Tag Breakdown:**
- `35=G` - MsgType: OrderCancelReplaceRequest
- `41=AMEND_QTY_001` - OrigClOrdID (order to amend)
- `11=AMEND_QTY_001_V2` - ClOrdID (new ID for amended order)
- `38=150` - OrderQty (new quantity: 150, was 100)
- `44=225.0` - Price (unchanged)

#### SEND: ExecutionReport - Replaced (ExecType=5)
```
8=FIX.4.2|9=166|35=8|49=BROKER|56=TEST_CLIENT|34=32|11=AMEND_QTY_001_V2|17=fd9aed0e|150=5|39=0|41=AMEND_QTY_001|55=AAPL|54=1|38=150|40=2|14=0|6=0|151=150|52=20251023-02:21:01.375|10=041|
```

**Tag Breakdown:**
- `35=8` - MsgType: ExecutionReport
- `11=AMEND_QTY_001_V2` - ClOrdID (new order ID)
- `150=5` - ExecType: Replaced (order amended)
- `39=0` - OrdStatus: New (back to New status after amend)
- `41=AMEND_QTY_001` - OrigClOrdID (original order ID)
- `38=150` - OrderQty (new quantity)
- `151=150` - LeavesQty (all 150 shares remaining)

### Example 2: Amend Price

#### RECV: Client amends price from $420.00 to $415.00
```
8=FIX.4.2|9=164|35=G|49=TEST_CLIENT|56=BROKER|34=3|52=20251023-02:21:01.826|41=AMEND_PRICE_001|11=AMEND_PRICE_001_V2|21=1|55=MSFT|54=2|60=20251023-02:21:01.826|40=2|44=415.0|38=50|10=131|
```

**Tag Breakdown:**
- `44=415.0` - Price (new price: $415.00, was $420.00)
- `38=50` - OrderQty (unchanged)

### Example 3: Amend Both Quantity and Price

#### RECV: Client amends both
```
8=FIX.4.2|9=163|35=G|49=TEST_CLIENT|56=BROKER|34=3|52=20251023-02:21:02.278|41=AMEND_BOTH_001|11=AMEND_BOTH_001_V2|21=1|55=GOOGL|54=1|60=20251023-02:21:02.278|40=2|44=170.0|38=75|10=060|
```

**Tag Breakdown:**
- `41=AMEND_BOTH_001` - OrigClOrdID
- `11=AMEND_BOTH_001_V2` - ClOrdID (new)
- `44=170.0` - Price (new price)
- `38=75` - OrderQty (new quantity)

---

## 10. OrderCancelReject for Amend (MsgType=9)

### Example: Cannot Amend Filled Order

#### RECV: Client tries to amend filled order
```
8=FIX.4.2|9=158|35=G|49=TEST_CLIENT|56=BROKER|34=3|52=20251023-02:21:02.965|41=AMEND_FILLED_001|11=AMEND_FILLED_001_V2|21=1|55=AAPL|54=1|60=20251023-02:21:02.965|40=2|38=100|10=123|
```

#### SEND: OrderCancelReject
```
8=FIX.4.2|9=139|35=9|49=BROKER|56=TEST_CLIENT|34=42|11=AMEND_FILLED_001_V2|41=AMEND_FILLED_001|39=0|434=0|58=Order already FILLED|52=20251023-02:21:02.970|10=172|
```

**Tag Breakdown:**
- `35=9` - MsgType: OrderCancelReject (also used for rejected amends)
- `434=0` - CxlRejReason: 0=Too late
- `58=Order already FILLED` - Text

---

## Summary

The logs show complete message flows for:

1. **Order Submission**: Client sends NewOrderSingle (D), receives ExecutionReport with ExecType=New (0)
2. **Order Execution**: Client receives ExecutionReport(s) with ExecType=PartialFill (1) or Fill (2)
3. **Client Cancel**: Client sends OrderCancelRequest (F), receives ExecutionReport with ExecType=Canceled (4) or OrderCancelReject (9)
4. **Client Amend**: Client sends OrderCancelReplaceRequest (G), receives ExecutionReport with ExecType=Replaced (5) or OrderCancelReject (9)
5. **Rejection Handling**: Server sends OrderCancelReject (9) when cancel/amend is not allowed

All messages include proper sequencing, checksums, and bidirectional RECV/SEND logging.
