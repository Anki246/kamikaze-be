# 🔧 Manual Verification Checklist

## 🚨 **CRITICAL: Follow This Exact Sequence**

The workflow is still failing because GitHub Actions permissions are not properly configured. Follow this **exact sequence** to fix the issue:

## ✅ **STEP 1: Verify Repository Access**

### **1.1 Check Repository Settings Access**
- [ ] Go to: https://github.com/Anki246/kamikaze-be/settings
- [ ] Verify you can access this page (no 404 or access denied)
- [ ] Confirm you see "Settings" tab in the repository navigation
- [ ] Check that you have "Admin" access (shown in repository sidebar)

**If you can't access this page:**
- You don't have admin permissions to this repository
- Contact the repository owner
- Or create a new personal repository for testing

## ✅ **STEP 2: Configure GitHub Actions (CRITICAL)**

### **2.1 Access Actions Settings**
- [ ] Go to: https://github.com/Anki246/kamikaze-be/settings/actions
- [ ] Verify you can access this page
- [ ] You should see "Actions permissions" and "Workflow permissions" sections

### **2.2 Configure Actions Permissions**
**Under "Actions permissions" section:**
- [ ] **Select**: "Allow all actions and reusable workflows"
- [ ] **DO NOT select**: "Disable actions" 
- [ ] **DO NOT select**: "Allow select actions and reusable workflows"

### **2.3 Configure Workflow Permissions**
**Under "Workflow permissions" section:**
- [ ] **Select**: "Read and write permissions"
- [ ] **Check**: "Allow GitHub Actions to create and approve pull requests"
- [ ] **DO NOT select**: "Read repository contents and packages permissions"

### **2.4 Save Settings**
- [ ] Click **"Save"** button at the bottom of the page
- [ ] Wait for the page to reload and confirm settings are saved

## ✅ **STEP 3: Add Repository Secrets**

### **3.1 Access Secrets Page**
- [ ] Go to: https://github.com/Anki246/kamikaze-be/settings/secrets/actions
- [ ] Verify you can access this page
- [ ] You should see "New repository secret" button

### **3.2 Add Test Secret First**
- [ ] Click "New repository secret"
- [ ] **Name**: `SIMPLE_TEST`
- [ ] **Value**: `hello`
- [ ] Click "Add secret"
- [ ] Verify it appears in the secrets list

### **3.3 Add AWS Credentials**
- [ ] Click "New repository secret"
- [ ] **Name**: `AWS_ACCESS_KEY_ID` (exact case)
- [ ] **Value**: Your AWS Access Key ID (starts with AKIA)
- [ ] Click "Add secret"

- [ ] Click "New repository secret"
- [ ] **Name**: `AWS_SECRET_ACCESS_KEY` (exact case)
- [ ] **Value**: Your AWS Secret Access Key (40 characters)
- [ ] Click "Add secret"

### **3.4 Add Additional Secrets**
- [ ] **Name**: `GROQ_API_KEY`
- [ ] **Value**: `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`

- [ ] **Name**: `RDS_MASTER_PASSWORD`
- [ ] **Value**: `admin2025Staging!`

### **3.5 Verify Secrets Added**
- [ ] Check that all secrets are listed on the secrets page
- [ ] Each secret should show "Updated X seconds ago"
- [ ] Values should be hidden (showing as ***)

## ✅ **STEP 4: Test Configuration**

### **4.1 Run Simple Test Workflow**
- [ ] Go to: https://github.com/Anki246/kamikaze-be/actions
- [ ] Find "Simple Secrets Test" workflow
- [ ] Click "Run workflow" dropdown
- [ ] Click "Run workflow" button
- [ ] Wait for workflow to complete

### **4.2 Check Test Results**
**Expected SUCCESS results:**
```
✅ GITHUB_TOKEN is available
✅ SIMPLE_TEST secret is accessible: hello
✅ AWS_ACCESS_KEY_ID is accessible
✅ AWS_SECRET_ACCESS_KEY is accessible
```

**If still FAILING:**
```
❌ GITHUB_TOKEN is NOT available
❌ SIMPLE_TEST secret is NOT accessible
```

## 🔍 **TROUBLESHOOTING**

### **Issue 1: Can't Access Repository Settings**
**Symptoms**: 404 or "You don't have access" on settings page
**Solution**: 
- Check if you're logged into the correct GitHub account
- Verify you have admin access to the repository
- Contact repository owner if needed

### **Issue 2: Actions Settings Not Available**
**Symptoms**: No "Actions" tab in repository settings
**Solution**:
- Repository might be in an organization with restricted Actions
- Contact organization admin
- Check organization-level Actions policies

### **Issue 3: Can't Save Actions Settings**
**Symptoms**: Settings don't save or revert back
**Solution**:
- Check for organization-level restrictions
- Ensure you have admin permissions
- Try refreshing page and saving again

### **Issue 4: Secrets Page Not Accessible**
**Symptoms**: Can't access secrets page or add secrets
**Solution**:
- Verify Actions are enabled first (Step 2)
- Check repository permissions
- Ensure no organization restrictions

### **Issue 5: Test Workflow Still Fails**
**Symptoms**: GITHUB_TOKEN still not available after configuration
**Solution**:
- Wait 5-10 minutes for settings to propagate
- Try running workflow again
- Check if repository is forked (forks have limited secret access)

## 🎯 **SUCCESS CRITERIA**

### **Configuration Complete When:**
- [ ] ✅ Can access all repository settings pages
- [ ] ✅ GitHub Actions is enabled with "Allow all actions"
- [ ] ✅ Workflow permissions set to "Read and write"
- [ ] ✅ All required secrets are added and visible
- [ ] ✅ Simple test workflow shows GITHUB_TOKEN available
- [ ] ✅ Simple test workflow shows secrets accessible

### **Ready for Main Pipeline When:**
- [ ] ✅ All above criteria met
- [ ] ✅ AWS credentials are valid and working
- [ ] ✅ Simple test workflow passes completely

## 📞 **If Still Failing After All Steps**

### **Possible Advanced Issues:**
1. **Repository is a fork**: Forks have limited secret access
2. **Organization restrictions**: Admin has disabled Actions/secrets
3. **Account-level issues**: GitHub account has restrictions
4. **Regional restrictions**: Some regions have limited GitHub features

### **Emergency Alternatives:**
1. **Create new personal repository** for testing
2. **Use different GitHub account** if current has restrictions
3. **Contact GitHub Support** for account-level issues

---

## 🚀 **IMMEDIATE ACTION PLAN**

### **RIGHT NOW (Next 10 minutes):**
1. ✅ **Follow Step 1**: Verify repository access
2. ✅ **Follow Step 2**: Configure GitHub Actions (CRITICAL)
3. ✅ **Follow Step 3**: Add repository secrets
4. ✅ **Follow Step 4**: Test with simple workflow

### **VERIFY SUCCESS:**
- Simple test workflow shows all secrets accessible
- GITHUB_TOKEN is available
- Ready to run main CI pipeline

**The key is following the exact sequence - Actions permissions FIRST, then secrets!**
