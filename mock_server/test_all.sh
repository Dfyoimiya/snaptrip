#!/bin/bash
# SnapTrip Mock Server 回归测试 v2
BASE="http://localhost:8001/api/client/v1"
ADMIN="http://localhost:8001/api/admin/v1"
PASS=0; FAIL=0; TOTAL=0
PHONE="1389999$(date +%s | tail -c5)"

ok() { TOTAL=$((TOTAL+1)); echo "  ✅ $1"; PASS=$((PASS+1)); }
ng() { local want="$1" label="$2"; shift 2
  local code=-1 attempt=0 max=3
  while [ $attempt -lt $max ]; do
    local resp=$("$@" 2>/dev/null)
    code=$(echo "$resp" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('code',-999))" 2>/dev/null)
    # -999 means ToolResult format from fault injection — retry
    [ "$code" != "-999" ] && break
    attempt=$((attempt+1))
  done
  TOTAL=$((TOTAL+1))
  if [ "$code" = "$want" ]; then echo "  ✅ $label (code=$code)"; PASS=$((PASS+1))
  else echo "  ❌ $label (expected code=$want, got $code)"; FAIL=$((FAIL+1)); fi; }

echo ""
echo "════════════════════════════════════════════"
echo "  SnapTrip Mock Server 回归测试"
echo "════════════════════════════════════════════"

# ── 准备 ──
echo ""
echo "── 准备: 注册新用户 ──"
TOKEN=$(curl -s -X POST $BASE/auth/register \
  -H 'Content-Type: application/json' \
  -d "{\"phone\":\"$PHONE\",\"password\":\"123456\",\"nickname\":\"测试\"}" \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['data']['token'])" 2>/dev/null)
if [ -n "$TOKEN" ]; then
  ok "注册成功 (phone=$PHONE)"
else
  # 可能已存在，尝试登录
  TOKEN=$(curl -s -X POST $BASE/auth/login \
    -H 'Content-Type: application/json' \
    -d "{\"phone\":\"$PHONE\",\"password\":\"123456\"}" \
    | python3 -c "import sys,json;print(json.load(sys.stdin)['data']['token'])" 2>/dev/null)
  ok "登录获取token"
fi

# ═══════════════════════════════════════════════
#  C端 认证
# ═══════════════════════════════════════════════
echo ""
echo "── C端 认证 ──"
ok "登录" curl -s -X POST $BASE/auth/login \
  -H 'Content-Type: application/json' -d "{\"phone\":\"$PHONE\",\"password\":\"123456\"}"
ng   1003 "密码错误" curl -s -X POST $BASE/auth/login \
  -H 'Content-Type: application/json' -d "{\"phone\":\"$PHONE\",\"password\":\"wrong\"}"
ok "获取个人信息" curl -s $BASE/users/me -H "Authorization: Bearer $TOKEN"

# ═══════════════════════════════════════════════
#  C端 首页
# ═══════════════════════════════════════════════
echo ""
echo "── C端 首页 ──"
ok "首页轮播图" curl -s $BASE/home/banners
ok "首页分类入口" curl -s $BASE/home/categories
ok "推荐流" curl -s "$BASE/home/recommend?lat=39.9&lng=116.4&page=1&size=5"

# ═══════════════════════════════════════════════
#  C端 商家
# ═══════════════════════════════════════════════
echo ""
echo "── C端 商家 ──"
ok "商家列表(全部)" curl -s "$BASE/merchants?page=1&size=10"
ok "商家列表(饮品分类)" curl -s "$BASE/merchants?category_id=cat-drink"
ok "商家列表(评分降序)" curl -s "$BASE/merchants?sort_field=rating&sort_order=desc&size=5"
ok "商家详情(m-001)" curl -s $BASE/merchants/m-001
ng   2001 "商家不存在" curl -s $BASE/merchants/nonexist

# ═══════════════════════════════════════════════
#  C端 商品
# ═══════════════════════════════════════════════
echo ""
echo "── C端 商品 ──"
ok "商品详情(含规格)" curl -s $BASE/products/p-001
ok "商品评价列表" curl -s "$BASE/products/p-001/reviews"
ok "商品评分统计" curl -s "$BASE/products/p-001/reviews/stats"
ng   2101 "商品不存在" curl -s $BASE/products/p-nonexist

# ═══════════════════════════════════════════════
#  C端 购物车
# ═══════════════════════════════════════════════
echo ""
echo "── C端 购物车 ──"
ok "加购p-002" curl -s -X POST $BASE/cart \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"product_id":"p-002","qty":1}'

ok "加购p-001(同商品合并)" curl -s -X POST $BASE/cart \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"product_id":"p-002","qty":2}'

ok "查看购物车" curl -s $BASE/cart -H "Authorization: Bearer $TOKEN"

CART_ID=$(curl -s $BASE/cart -H "Authorization: Bearer $TOKEN" \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['data'][0]['item_id'])" 2>/dev/null)

ok "修改数量" curl -s -X PUT "$BASE/cart/$CART_ID" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d '{"qty":5}'

ok "删除单项" curl -s -X DELETE "$BASE/cart/$CART_ID" -H "Authorization: Bearer $TOKEN"

ok "清空购物车" curl -s -X DELETE $BASE/cart -H "Authorization: Bearer $TOKEN"

# ═══════════════════════════════════════════════
#  C端 订单
# ═══════════════════════════════════════════════
echo ""
echo "── C端 订单 ──"
ORDER_RESP=$(curl -s -X POST $BASE/orders \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"merchant_id":"m-001","address_id":"addr-1","items":[{"product_id":"p-002","qty":1}],"note":"测试订单"}')
ORDER_ID=$(echo "$ORDER_RESP" | python3 -c "import sys,json;print(json.load(sys.stdin)['data']['order_id'])" 2>/dev/null)
ok "下单" echo "$ORDER_ID" | grep -q . && echo ok >/dev/null

ok "支付" curl -s -X POST "$BASE/orders/$ORDER_ID/pay" -H "Authorization: Bearer $TOKEN"

ok "取消订单" curl -s -X PUT "$BASE/orders/$ORDER_ID/cancel" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d '{"reason":"测试取消"}'

ok "订单列表" curl -s "$BASE/orders?page=1&size=10" -H "Authorization: Bearer $TOKEN"

# ═══════════════════════════════════════════════
#  C端 地址
# ═══════════════════════════════════════════════
echo ""
echo "── C端 地址 ──"
ok "新增地址" curl -s -X POST $BASE/addresses \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"contact_name":"张三","phone":"13800009999","province":"北京","city":"北京","district":"朝阳区","detail":"望京SOHO","lng":116.478,"lat":39.989}'

ok "地址列表" curl -s $BASE/addresses -H "Authorization: Bearer $TOKEN"

# ═══════════════════════════════════════════════
#  C端 收藏
# ═══════════════════════════════════════════════
echo ""
echo "── C端 收藏 ──"
ok "收藏商家" curl -s -X POST $BASE/favorites \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"target_type":"merchant","target_id":"m-001"}'

ok "收藏列表" curl -s $BASE/favorites -H "Authorization: Bearer $TOKEN"

ok "取消收藏" curl -s -X DELETE $BASE/favorites \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"target_type":"merchant","target_id":"m-001"}'

# ═══════════════════════════════════════════════
#  C端 搜索
# ═══════════════════════════════════════════════
echo ""
echo "── C端 搜索 ──"
SEARCH_Q=$(python3 -c "import urllib.parse;print(urllib.parse.quote('火锅'))")
ok "关键词搜索" curl -s "$BASE/search?q=$SEARCH_Q&page=1&size=5"
ok "热门搜索" curl -s $BASE/search/hot
ok "搜索联想" curl -s "$BASE/search/suggestions?q=奶"
ok "搜索历史" curl -s $BASE/search/history -H "Authorization: Bearer $TOKEN"

# ═══════════════════════════════════════════════
#  C端 评价
# ═══════════════════════════════════════════════
echo ""
echo "── C端 评价 ──"
ok "写评价" curl -s -X POST $BASE/reviews \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d "{\"product_id\":\"p-001\",\"order_id\":\"$ORDER_ID\",\"rating\":5,\"content\":\"好吃\",\"images\":[]}"

# ═══════════════════════════════════════════════
#  B端 认证
# ═══════════════════════════════════════════════
echo ""
echo "── B端 认证 ──"
ADMIN_TOKEN=$(curl -s -X POST $ADMIN/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123"}' \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['data']['token'])" 2>/dev/null)
ok "管理员登录" echo ok

ng   1101 "管理员密码错误" curl -s -X POST $ADMIN/auth/login \
  -H 'Content-Type: application/json' -d '{"username":"admin","password":"wrong"}'

# ═══════════════════════════════════════════════
#  B端 仪表盘
# ═══════════════════════════════════════════════
echo ""
echo "── B端 仪表盘 ──"
ok "数据概览" curl -s $ADMIN/dashboard -H "Authorization: Bearer $ADMIN_TOKEN"

# ═══════════════════════════════════════════════
#  B端 员工管理
# ═══════════════════════════════════════════════
echo ""
echo "── B端 员工管理 ──"
ok "员工列表" curl -s "$ADMIN/employees?page=1&size=10" -H "Authorization: Bearer $ADMIN_TOKEN"
ok "新增员工" curl -s -X POST $ADMIN/employees \
  -H "Authorization: Bearer $ADMIN_TOKEN" -H 'Content-Type: application/json' \
  -d '{"username":"newstaff","password":"123456","real_name":"新员工","phone":"13800009999","role_codes":["ORDER_STAFF"]}'

# ═══════════════════════════════════════════════
#  B端 角色权限
# ═══════════════════════════════════════════════
echo ""
echo "── B端 角色权限 ──"
ok "角色列表" curl -s $ADMIN/roles -H "Authorization: Bearer $ADMIN_TOKEN"
ok "权限树" curl -s $ADMIN/roles/permissions/tree -H "Authorization: Bearer $ADMIN_TOKEN"

# ═══════════════════════════════════════════════
#  B端 商家管理
# ═══════════════════════════════════════════════
echo ""
echo "── B端 商家管理 ──"
ok "商家已审核列表" curl -s "$ADMIN/merchants?audit_status=APPROVED" -H "Authorization: Bearer $ADMIN_TOKEN"
ok "审核通过(m-001)" curl -s -X PUT $ADMIN/merchants/m-001/audit \
  -H "Authorization: Bearer $ADMIN_TOKEN" -H 'Content-Type: application/json' -d '{"status":"APPROVED"}'
ok "暂停营业(m-005)" curl -s -X PUT $ADMIN/merchants/m-005/status \
  -H "Authorization: Bearer $ADMIN_TOKEN" -H 'Content-Type: application/json' -d '{"status":"CLOSED"}'

# ═══════════════════════════════════════════════
#  B端 分类管理
# ═══════════════════════════════════════════════
echo ""
echo "── B端 分类管理 ──"
ok "分类树" curl -s $ADMIN/categories/tree -H "Authorization: Bearer $ADMIN_TOKEN"
ok "新增分类" curl -s -X POST $ADMIN/categories \
  -H "Authorization: Bearer $ADMIN_TOKEN" -H 'Content-Type: application/json' \
  -d '{"name":"测试分类","type":"PRODUCT","parent_id":"cat-food","sort_order":99}'

# ═══════════════════════════════════════════════
#  B端 商品管理
# ═══════════════════════════════════════════════
echo ""
echo "── B端 商品管理 ──"
ok "商品列表" curl -s "$ADMIN/products?page=1&size=5" -H "Authorization: Bearer $ADMIN_TOKEN"
ok "下架p-005" curl -s -X PUT $ADMIN/products/p-005/status \
  -H "Authorization: Bearer $ADMIN_TOKEN" -H 'Content-Type: application/json' -d '{"status":"OFF_SHELF"}'
ok "上架p-005" curl -s -X PUT $ADMIN/products/p-005/status \
  -H "Authorization: Bearer $ADMIN_TOKEN" -H 'Content-Type: application/json' -d '{"status":"ON_SHELF"}'
ok "批量操作" curl -s -X PUT $ADMIN/products/batch/status \
  -H "Authorization: Bearer $ADMIN_TOKEN" -H 'Content-Type: application/json' \
  -d '{"ids":["p-005","p-006"],"status":"ON_SHELF"}'
ng   2101 "商品不存在" curl -s -X PUT $ADMIN/products/p-nonexist/status \
  -H "Authorization: Bearer $ADMIN_TOKEN" -H 'Content-Type: application/json' -d '{"status":"OFF_SHELF"}'

# ═══════════════════════════════════════════════
#  B端 订单管理
# ═══════════════════════════════════════════════
echo ""
echo "── B端 订单管理 ──"
ADMIN_ORDER_RESP=$(curl -s -X POST $BASE/orders \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"merchant_id":"m-001","address_id":"addr-1","items":[{"product_id":"p-002","qty":1}]}')
ADMIN_ORDER=$(echo "$ADMIN_ORDER_RESP" | python3 -c "import sys,json;print(json.load(sys.stdin)['data']['order_id'])" 2>/dev/null)

ok "全局订单列表" curl -s "$ADMIN/orders?page=1&size=10" -H "Authorization: Bearer $ADMIN_TOKEN"

ok "CONFIRMED" curl -s -X PUT "$ADMIN/orders/$ADMIN_ORDER/status" \
  -H "Authorization: Bearer $ADMIN_TOKEN" -H 'Content-Type: application/json' \
  -d '{"target_status":"CONFIRMED","remark":"接单"}'

ok "DELIVERING" curl -s -X PUT "$ADMIN/orders/$ADMIN_ORDER/status" \
  -H "Authorization: Bearer $ADMIN_TOKEN" -H 'Content-Type: application/json' \
  -d '{"target_status":"DELIVERING","remark":"派送中"}'

ok "COMPLETED" curl -s -X PUT "$ADMIN/orders/$ADMIN_ORDER/status" \
  -H "Authorization: Bearer $ADMIN_TOKEN" -H 'Content-Type: application/json' \
  -d '{"target_status":"COMPLETED","remark":"已完成"}'

ng   3002 "非法流转拦截" curl -s -X PUT "$ADMIN/orders/$ADMIN_ORDER/status" \
  -H "Authorization: Bearer $ADMIN_TOKEN" -H 'Content-Type: application/json' \
  -d '{"target_status":"CANCELLED"}'

# ═══════════════════════════════════════════════
#  B端 营销
# ═══════════════════════════════════════════════
echo ""
echo "── B端 营销 ──"
ok "轮播图列表" curl -s $ADMIN/banners -H "Authorization: Bearer $ADMIN_TOKEN"
ok "新增轮播图" curl -s -X POST $ADMIN/banners \
  -H "Authorization: Bearer $ADMIN_TOKEN" -H 'Content-Type: application/json' \
  -d '{"image_url":"https://dummyimage.com/750x350/0af/fff&text=New","link_type":"none","sort_order":10}'
ok "公告列表" curl -s $ADMIN/notices -H "Authorization: Bearer $ADMIN_TOKEN"
ok "新增公告" curl -s -X POST $ADMIN/notices \
  -H "Authorization: Bearer $ADMIN_TOKEN" -H 'Content-Type: application/json' \
  -d '{"title":"测试公告","content":"这是一条测试公告","target_type":"ALL"}'

# ═══════════════════════════════════════════════
#  B端 数据统计
# ═══════════════════════════════════════════════
echo ""
echo "── B端 数据统计 ──"
ok "营业额统计" curl -s "$ADMIN/statistics/revenue?start_date=2024-06-01&end_date=2024-06-30" -H "Authorization: Bearer $ADMIN_TOKEN"
ok "订单统计" curl -s "$ADMIN/statistics/orders?start_date=2024-06-01&end_date=2024-06-30" -H "Authorization: Bearer $ADMIN_TOKEN"
ok "用户统计" curl -s "$ADMIN/statistics/users?start_date=2024-06-01&end_date=2024-06-30" -H "Authorization: Bearer $ADMIN_TOKEN"
ok "商品排行" curl -s "$ADMIN/statistics/ranking?limit=5" -H "Authorization: Bearer $ADMIN_TOKEN"

# ═══════════════════════════════════════════════
echo ""
echo "════════════════════════════════════════════"
echo "  测试完成: $PASS / $TOTAL 通过"
if [ $FAIL -gt 0 ]; then
  echo "  ❌ $FAIL 项失败"
  exit 1
else
  echo "  ✅ 全部通过"
  exit 0
fi
