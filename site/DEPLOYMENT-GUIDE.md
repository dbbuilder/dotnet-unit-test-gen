# Deployment Guide: test-agent.servicevision.io

**Date**: October 23, 2025
**Domain**: test-agent.servicevision.io
**Platform**: Vercel

---

## 📋 Prerequisites

- Vercel CLI installed (`npm install -g vercel`)
- Vercel account with access to ServiceVision project
- Name.com API credentials (from CLAUDE.md)

---

## 🚀 Deployment Steps

### Step 1: Deploy to Vercel

```bash
cd /mnt/d/dev2/dotnet-unit-test-gen/site

# Deploy to Vercel (interactive)
vercel --prod

# OR deploy with project name specified
vercel --prod --name dotnet-test-generator
```

**Follow prompts**:
- Set up and deploy? Yes
- Which scope? (select your account/team)
- Link to existing project? No (first time) / Yes (subsequent deployments)
- What's your project's name? `dotnet-test-generator`
- In which directory is your code located? `./` (current directory)
- Want to override the settings? No

**Expected Output**:
```
✔  Deployed to production. https://dotnet-test-generator-abc123.vercel.app
```

---

### Step 2: Configure Custom Domain in Vercel Dashboard

1. Go to https://vercel.com/dashboard
2. Select project: `dotnet-test-generator`
3. Click **Settings** → **Domains**
4. Add domain: `test-agent.servicevision.io`
5. Vercel will provide DNS records to add

**Vercel DNS Records** (example):
```
Type: CNAME
Name: test-agent
Value: cname.vercel-dns.com
```

OR

```
Type: A
Name: test-agent
Value: 76.76.19.19
```

---

### Step 3: Configure DNS in Name.com

**Using Name.com API** (recommended for automation):

```bash
# Name.com API credentials (from CLAUDE.md)
USERNAME="TEDTHERRIAULT"
TOKEN="4790fea6e456f7fe9cf4f61a30f025acd63ecd1c"
DOMAIN="servicevision.io"

# Create CNAME record for test-agent subdomain
curl -u "$USERNAME:$TOKEN" \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "host": "test-agent",
    "type": "CNAME",
    "answer": "cname.vercel-dns.com",
    "ttl": 300
  }' \
  "https://api.name.com/v4/domains/$DOMAIN/records"
```

**Using Name.com Dashboard** (manual):

1. Go to https://www.name.com/account/domain/details/servicevision.io#dns
2. Click **Add Record**
3. Configure:
   - **Type**: CNAME
   - **Host**: test-agent
   - **Answer**: cname.vercel-dns.com (or A record IP from Vercel)
   - **TTL**: 300 (5 minutes)
4. Click **Add Record**

---

### Step 4: Verify Deployment

**Wait for DNS propagation** (usually 5-15 minutes, max 48 hours):

```bash
# Check DNS propagation
dig test-agent.servicevision.io

# Check CNAME record
dig CNAME test-agent.servicevision.io

# Test HTTPS endpoint
curl -I https://test-agent.servicevision.io
```

**Expected Result**:
- HTTP 200 OK
- HTTPS with valid SSL certificate (auto-provisioned by Vercel)
- Site loads correctly at https://test-agent.servicevision.io

---

## 🔄 Subsequent Deployments

After initial setup, deploy updates with:

```bash
cd /mnt/d/dev2/dotnet-unit-test-gen/site
vercel --prod
```

Vercel will:
- Build and deploy automatically
- Update the production URL
- Maintain custom domain configuration

---

## 🛠️ Vercel CLI Commands

```bash
# Deploy to production
vercel --prod

# Deploy to preview (staging)
vercel

# List deployments
vercel list

# Check project info
vercel inspect

# Add domain via CLI
vercel domains add test-agent.servicevision.io

# List domains
vercel domains ls

# Remove domain
vercel domains rm test-agent.servicevision.io
```

---

## 📁 Deployment Structure

Vercel will deploy these files:
```
site/
├── index.html         # Main page
├── css/
│   └── style.css     # Styling
├── js/
│   └── main.js       # Interactivity
└── vercel.json       # Vercel configuration
```

---

## 🔐 Environment Configuration

No environment variables needed for this static site deployment.

---

## 📊 Monitoring & Analytics

**Vercel Dashboard**:
- View real-time analytics: https://vercel.com/dashboard
- Monitor bandwidth, requests, errors
- View deployment logs

**Performance**:
- Global CDN (automatic)
- HTTPS with auto-renewal
- Instant cache invalidation on deploy

---

## 🐛 Troubleshooting

### Issue: Domain not resolving
**Solution**: Wait for DNS propagation (up to 48 hours). Check with `dig test-agent.servicevision.io`

### Issue: SSL certificate error
**Solution**: Vercel auto-provisions SSL. If not working after 24 hours, contact Vercel support.

### Issue: 404 on deployed site
**Solution**: Ensure `index.html` is in root of deployed directory. Check `vercel.json` configuration.

### Issue: CSS/JS not loading
**Solution**: Check relative paths in `index.html`. Paths should be relative (`css/style.css`, not `/css/style.css`).

---

## 📝 Name.com DNS Record Details

**Current servicevision.io DNS** (for reference):

To view existing DNS records:
```bash
curl -u "TEDTHERRIAULT:4790fea6e456f7fe9cf4f61a30f025acd63ecd1c" \
  https://api.name.com/v4/domains/servicevision.io/records
```

To add the test-agent CNAME:
```bash
curl -u "TEDTHERRIAULT:4790fea6e456f7fe9cf4f61a30f025acd63ecd1c" \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "host": "test-agent",
    "type": "CNAME",
    "answer": "cname.vercel-dns.com",
    "ttl": 300
  }' \
  https://api.name.com/v4/domains/servicevision.io/records
```

---

## ✅ Deployment Checklist

### Pre-Deployment
- [x] Vercel CLI installed
- [x] Site files ready in `/mnt/d/dev2/dotnet-unit-test-gen/site`
- [x] vercel.json created
- [ ] Vercel account logged in (`vercel login`)

### Deployment
- [ ] Run `vercel --prod` in site directory
- [ ] Note Vercel deployment URL
- [ ] Note DNS records provided by Vercel

### DNS Configuration
- [ ] Add CNAME record in Name.com for `test-agent.servicevision.io`
- [ ] Verify DNS propagation (`dig test-agent.servicevision.io`)

### Verification
- [ ] Site accessible at https://test-agent.servicevision.io
- [ ] SSL certificate valid
- [ ] All pages load correctly
- [ ] CSS and JS assets load
- [ ] ROI calculator works
- [ ] Contact form works (mailto link)

---

## 🎯 Success Criteria

Deployment is successful when:
1. ✅ Site loads at https://test-agent.servicevision.io
2. ✅ HTTPS with valid SSL certificate
3. ✅ All styling (CSS) loads correctly
4. ✅ All JavaScript functionality works (ROI calculator, form)
5. ✅ Page is responsive on mobile/desktop
6. ✅ No console errors in browser dev tools

---

## 🔗 Important Links

- **Live Site** (after deployment): https://test-agent.servicevision.io
- **Vercel Dashboard**: https://vercel.com/dashboard
- **Name.com Dashboard**: https://www.name.com/account/domain/details/servicevision.io#dns
- **Name.com API Docs**: https://www.name.com/api-docs

---

## 📞 Support

- **Vercel Support**: https://vercel.com/support
- **Name.com Support**: https://www.name.com/support
- **API Token (Name.com)**: 4790fea6e456f7fe9cf4f61a30f025acd63ecd1c

---

**Created**: October 23, 2025
**Last Updated**: October 23, 2025
**Status**: Ready for deployment
