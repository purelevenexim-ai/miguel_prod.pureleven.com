# AI Token Optimization - Prompt Guide

**Goal:** Reduce AI token consumption by 95% through smart indexing and focused prompts.

---

## 🎯 Rules for Efficient Prompts

### ❌ DON'T DO THIS

```markdown
Read /opt/pureleven/backend/app/modules/orders/service.py

I need to understand how the order_create function works and 
I want to add support for handling bulk orders. Can you explain 
the entire module and show me step by step how to modify it?
```

**Problem:** Loads 1,200 LOC file + AI writes 3,000 token response = **4,200 tokens wasted**

---

### ✅ DO THIS INSTEAD

```markdown
# Task: Add bulk order support to Order module

## Using indexed data:
- Check .claude/index/codebase-structure.json → orders module
- Find order_create location in .claude/index/key-files-registry.json
- Schema reference: .claude/index/database-schema.json → orders table

## Question format:
Order.create() currently handles 1 order. How do I modify it to accept 
list[Order] for bulk creation? (Show only the necessary code changes)

## Response format:
- Current code (5 lines)
- Required changes (10 lines)
- Database impact (3 lines)
- Related files to update (file list)
```

**Result:** Load 50 LOC index + AI writes 500 token response = **550 tokens** (87% reduction!)

---

## 📋 Prompt Template Checklist

For every AI request, use this checklist:

- [ ] **Reference indices** — Use `.claude/index/` instead of files
- [ ] **Specify line numbers** — "backend/app/modules/orders/router.py:45-120"
- [ ] **Set response format** — "Respond with: Current Code → Changes → Impact"
- [ ] **Add constraints** — "Max 200 words", "No introductions", "Code examples only"
- [ ] **Name the task** — "# Task: Add field to Order"
- [ ] **Avoid re-context** — Save conversation state in `.claude/conversations/session-name.json`

---

## 🔍 Index Files Reference

### When to use which index:

| Need | Use This | Load Time |
|------|----------|-----------|
| "How does the orders module work?" | codebase-structure.json | 50 tokens |
| "What APIs exist?" | api-endpoints.json | 80 tokens |
| "Where is order_create?" | key-files-registry.json | 40 tokens |
| "What's the database schema?" | database-schema.json | 60 tokens |
| "How does it integrate with Shopify?" | integration-map.json | 50 tokens |
| "All of the above" | LOAD ALL INDICES | 280 tokens |

**NEVER load:** Raw code files (1000s of tokens) — use indices instead!

---

## 💬 Example Conversations

### Example 1: "Add customer_notes field to Order"

**Token Budget:** 500 tokens (target)

#### ❌ Bad Approach (3,000 tokens)
```
User: How do I add customer_notes field to the Order model?

AI: [Loads entire models.py, service.py, router.py files]
AI: [Writes comprehensive 1,500-word explanation with examples]
Total: 3,000+ tokens
```

#### ✅ Good Approach (400 tokens)
```
User:
# Task: Add customer_notes field to Order

Using .claude/index/database-schema.json → orders table
Using .claude/index/key-files-registry.json

Question: How to add customer_notes string field to Order?

Format: 
1. Model change (lines)
2. Migration name + code (5 lines)
3. Files to update (list)
4. API endpoint changes (if any)

User: [Provides conversation state from .claude/conversations/add-order-field.json]

AI: [Uses cached context, provides only necessary changes]
Total: 400 tokens
```

---

### Example 2: "Debug: Message not sending to WhatsApp"

**Token Budget:** 300 tokens (target)

#### ❌ Bad Approach (2,500 tokens)
```
User: Messages aren't sending. Can you explain the entire 
message automation system and help me debug?

AI: [Loads message_automation/service.py: 3,167 LOC]
AI: [Explains entire system: 1,200 token explanation]
AI: [Lists possible issues: 500 tokens]
Total: 2,500+ tokens
```

#### ✅ Good Approach (280 tokens)
```
User:
# Task: Debug - Message not sending to WhatsApp

Context: Message for order PRN-260620-123 to 9447744583 
stuck in "pending" status for 6 hours.

Using .claude/index/:
- message-automation/service.py flow (lines 500-600)
- whatsapp/wabis_service.py error handling

Question: What are the 3 most common causes and how to check each?

Format: Each cause = 2-line description + 1-line query/log command

User: [Loads conversation state with error logs already attached]

AI: [Uses context, lists 3 specific checks with queries]
Total: 280 tokens
```

---

## 📝 Response Format Templates

### Template 1: "Explain Function"

```markdown
## Function: order_create()

**File:** backend/app/modules/orders/service.py:45

**Purpose:** [1-sentence]

**Steps:**
1. [Step 1]
2. [Step 2]
3. [Step 3]

**Returns:** [Type]

**Related:** [3 related functions]
```

**Word limit:** 150 words

---

### Template 2: "How to Add Field"

```markdown
## Add customer_notes to Order

**Step 1 - Model**
[2-3 lines of code]

**Step 2 - Migration**
[2-3 lines of code]

**Step 3 - API**
[2-3 lines of code]

**Files:** orders/models.py, orders/router.py, alembic/versions/00XX.py
```

**Word limit:** 100 words

---

### Template 3: "Debug Issue"

```markdown
## Issue: [Title]

**Cause 1:** [Cause]
Check: [1-line command]

**Cause 2:** [Cause]
Check: [1-line command]

**Cause 3:** [Cause]
Check: [1-line command]

**Most Likely:** Cause 2 (reason)
```

**Word limit:** 80 words

---

## 🚀 Quick Start

### First Time Setup (5 minutes)

```bash
# 1. Create conversation state file
cat > /opt/pureleven/.claude/conversations/my-session.json << 'EOF'
{
  "session_name": "my-session",
  "task": "Add delivery_notes field to Order",
  "context": {
    "module": "orders",
    "affected_files": ["models.py", "router.py"],
    "database_impact": "New column in orders table"
  },
  "files_touched": [],
  "decisions_made": []
}
EOF

# 2. Next AI conversation, reference this file:
# "Load .claude/conversations/my-session.json for context..."
```

### Per-Conversation Process

1. **Start:** Create new conversation JSON in `.claude/conversations/`
2. **Ask:** Reference indices + conversation state
3. **Respond:** AI uses loaded context (no re-explaining)
4. **Update:** Add decisions to conversation state
5. **End:** Save conversation JSON for next time

---

## 📊 Track Token Usage

Create tracking file:

```bash
cat > /opt/pureleven/.claude/token-tracker.json << 'EOF'
{
  "sessions": [
    {
      "date": "2026-06-20",
      "task": "Add customer_notes field",
      "tokens_before_optimization": 3000,
      "tokens_after_optimization": 350,
      "reduction_percent": 88.3,
      "prompt_followed_guide": true
    }
  ]
}
EOF
```

After each session, add entry and track savings!

---

## ✅ Pre-Prompt Checklist

Before asking AI, verify:

- [ ] Checking `.claude/index/` for needed info?
- [ ] Using conversation state file (`.claude/conversations/...json`)?
- [ ] Specified exact file paths + line numbers?
- [ ] Added response format constraint?
- [ ] Added word/section limit?
- [ ] Avoided asking to "read full file" or "explain everything"?
- [ ] Question is specific (not open-ended)?

**If any ❌, refine prompt first!**

---

## 🎯 Token Budget by Task Type

| Task | Budget | Approach |
|------|--------|----------|
| Explain module | 500 | Use index + 1 example function |
| Add field | 300 | Use index + template |
| Debug issue | 250 | Use index + 3 causes |
| Code review | 400 | Use index + 5 key sections |
| Architecture question | 600 | Use integration-map.json + diagram |
| Refactor function | 350 | Use indexed location + changes only |

---

**Remember:** If your prompt loads 50+ lines of code, it's wrong. Use indices!

---

*Generated: June 20, 2026 | Token Optimization v1.0*
