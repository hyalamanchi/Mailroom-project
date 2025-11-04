/**
 * Google Apps Script for CP2000 Case Management
 * Add this script to your Google Sheet to enable automatic processing
 * 
 * HOW TO ADD:
 * 1. Open your Google Sheet
 * 2. Go to Extensions > Apps Script
 * 3. Delete any existing code
 * 4. Paste this entire script
 * 5. Click Save (disk icon)
 * 6. Run 'onOpen' once to authorize
 * 7. Refresh your sheet to see the custom menu
 */

/**
 * Creates custom menu when sheet opens
 */
function onOpen() {
  var ui = SpreadsheetApp.getUi();
  ui.createMenu('🤖 CP2000 Automation')
      .addItem('✅ Process All Approved Cases', 'processApprovedCases')
      .addItem('📊 Show Approval Summary', 'showApprovalSummary')
      .addItem('🔄 Enable Auto-Processing', 'enableAutoProcessing')
      .addItem('⚙️ Setup Webhook URL', 'setupWebhook')
      .addSeparator()
      .addItem('📝 Mark Selected as Approve', 'markSelectedAsApprove')
      .addItem('❌ Mark Selected as Reject', 'markSelectedAsReject')
      .addItem('📋 Mark Selected as Review', 'markSelectedAsReview')
      .addToUi();
}

/**
 * Mark selected rows as Approve
 */
function markSelectedAsApprove() {
  markSelectedRows('Approve');
}

/**
 * Mark selected rows as Reject
 */
function markSelectedAsReject() {
  markSelectedRows('Reject');
}

/**
 * Mark selected rows as Review
 */
function markSelectedAsReview() {
  markSelectedRows('Review');
}

/**
 * Helper function to mark selected rows with a status
 */
function markSelectedRows(status) {
  var sheet = SpreadsheetApp.getActiveSheet();
  var selection = sheet.getActiveRange();
  var startRow = selection.getRow();
  var numRows = selection.getNumRows();
  
  // Update Status column (column A)
  for (var i = 0; i < numRows; i++) {
    var row = startRow + i;
    if (row > 1) { // Skip header
      sheet.getRange(row, 1).setValue(status);
      
      // Apply color coding
      var cell = sheet.getRange(row, 1);
      if (status === 'Approve') {
        cell.setBackground('#b7e1cd'); // Green
        cell.setFontWeight('bold');
      } else if (status === 'Reject') {
        cell.setBackground('#f4c7c3'); // Red
        cell.setFontWeight('bold');
      } else if (status === 'Review') {
        cell.setBackground('#fff2cc'); // Yellow
        cell.setFontWeight('normal');
      }
    }
  }
  
  SpreadsheetApp.getUi().alert(`✅ Marked ${numRows} row(s) as "${status}"`);
}

/**
 * Process all approved cases
 */
function processApprovedCases() {
  var ui = SpreadsheetApp.getUi();
  var sheet = SpreadsheetApp.getActiveSheet();
  var data = sheet.getDataRange().getValues();
  
  var approvedCount = 0;
  var processedRows = [];
  
  // Count approved cases
  for (var i = 1; i < data.length; i++) { // Skip header
    var status = data[i][0]; // Column A
    var processingStatus = data[i][18]; // Column S (Processing Status)
    
    if (status === 'Approve' && processingStatus !== 'Completed') {
      approvedCount++;
      processedRows.push(i + 1);
    }
  }
  
  if (approvedCount === 0) {
    ui.alert('ℹ️ No Approved Cases', 
             'No cases are marked as "Approve" or all approved cases have already been processed.', 
             ui.ButtonSet.OK);
    return;
  }
  
  // Confirm processing
  var response = ui.alert(
    '🚀 Process Approved Cases?',
    `Found ${approvedCount} approved case(s) ready for processing.\n\n` +
    'This will:\n' +
    '✅ Create tasks in Logics\n' +
    '📤 Upload documents to cases\n' +
    '📝 Update processing status\n\n' +
    'Do you want to continue?',
    ui.ButtonSet.YES_NO
  );
  
  if (response === ui.Button.YES) {
    // Mark as processing
    for (var i = 0; i < processedRows.length; i++) {
      sheet.getRange(processedRows[i], 19).setValue('Queued for Processing'); // Column S
    }
    
    // Get webhook URL from script properties
    var webhookUrl = PropertiesService.getScriptProperties().getProperty('WEBHOOK_URL');
    
    if (webhookUrl) {
      // Trigger webhook
      triggerWebhook(webhookUrl, approvedCount);
      ui.alert('✅ Processing Started', 
               `${approvedCount} case(s) have been queued for processing.\n\n` +
               'The automation script will process them shortly.\n' +
               'Check the "Processing Status" column for updates.',
               ui.ButtonSet.OK);
    } else {
      ui.alert('⚠️ Manual Processing Required',
               `${approvedCount} case(s) are ready for processing.\n\n` +
               'Run this command in your terminal:\n\n' +
               'python3 sheet_approval_automation.py [SHEET_ID] once\n\n' +
               'Or set up a webhook URL in the menu.',
               ui.ButtonSet.OK);
    }
  }
}

/**
 * Show summary of approval statuses
 */
function showApprovalSummary() {
  var sheet = SpreadsheetApp.getActiveSheet();
  var data = sheet.getDataRange().getValues();
  
  var counts = {
    'Approve': 0,
    'Reject': 0,
    'Review': 0,
    'Completed': 0
  };
  
  for (var i = 1; i < data.length; i++) { // Skip header
    var status = data[i][0]; // Column A
    var processingStatus = data[i][18]; // Column S
    
    if (counts.hasOwnProperty(status)) {
      counts[status]++;
    }
    
    if (processingStatus === 'Completed') {
      counts['Completed']++;
    }
  }
  
  var message = '📊 Case Status Summary\n\n' +
                `✅ Approved: ${counts['Approve']}\n` +
                `❌ Rejected: ${counts['Reject']}\n` +
                `📋 Under Review: ${counts['Review']}\n` +
                `🎯 Completed: ${counts['Completed']}\n\n` +
                `Total Cases: ${data.length - 1}`;
  
  SpreadsheetApp.getUi().alert(message);
}

/**
 * Setup webhook URL for automatic processing
 */
function setupWebhook() {
  var ui = SpreadsheetApp.getUi();
  var currentUrl = PropertiesService.getScriptProperties().getProperty('WEBHOOK_URL') || '';
  
  var response = ui.prompt(
    '⚙️ Setup Webhook URL',
    'Enter the webhook URL for automatic processing:\n\n' +
    '(Leave blank to disable webhook)\n\n' +
    'Current: ' + (currentUrl || 'Not set'),
    ui.ButtonSet.OK_CANCEL
  );
  
  if (response.getSelectedButton() === ui.Button.OK) {
    var url = response.getResponseText().trim();
    
    if (url) {
      PropertiesService.getScriptProperties().setProperty('WEBHOOK_URL', url);
      ui.alert('✅ Webhook URL saved successfully!');
    } else {
      PropertiesService.getScriptProperties().deleteProperty('WEBHOOK_URL');
      ui.alert('ℹ️ Webhook URL cleared');
    }
  }
}

/**
 * Enable auto-processing with time-based trigger
 */
function enableAutoProcessing() {
  var ui = SpreadsheetApp.getUi();
  
  var response = ui.alert(
    '🔄 Enable Auto-Processing',
    'This will automatically check for approved cases every 5 minutes.\n\n' +
    'Note: You still need to run the Python automation script.\n' +
    'This just queues cases for processing.\n\n' +
    'Continue?',
    ui.ButtonSet.YES_NO
  );
  
  if (response === ui.Button.YES) {
    // Create time-based trigger
    ScriptApp.newTrigger('autoProcessApproved')
        .timeBased()
        .everyMinutes(5)
        .create();
    
    ui.alert('✅ Auto-Processing Enabled',
             'The sheet will now check for approved cases every 5 minutes.\n\n' +
             'To disable, go to Extensions > Apps Script > Triggers and delete the trigger.',
             ui.ButtonSet.OK);
  }
}

/**
 * Auto-process function (called by trigger)
 */
function autoProcessApproved() {
  var sheet = SpreadsheetApp.getActiveSheet();
  var data = sheet.getDataRange().getValues();
  
  var approvedCount = 0;
  
  for (var i = 1; i < data.length; i++) {
    var status = data[i][0];
    var processingStatus = data[i][18];
    
    if (status === 'Approve' && processingStatus !== 'Completed' && processingStatus !== 'Queued for Processing') {
      sheet.getRange(i + 1, 19).setValue('Queued for Processing');
      approvedCount++;
    }
  }
  
  if (approvedCount > 0) {
    var webhookUrl = PropertiesService.getScriptProperties().getProperty('WEBHOOK_URL');
    if (webhookUrl) {
      triggerWebhook(webhookUrl, approvedCount);
    }
  }
}

/**
 * Trigger webhook notification
 */
function triggerWebhook(url, count) {
  try {
    var payload = {
      'event': 'cases_approved',
      'count': count,
      'spreadsheet_id': SpreadsheetApp.getActiveSpreadsheet().getId(),
      'timestamp': new Date().toISOString()
    };
    
    var options = {
      'method': 'post',
      'contentType': 'application/json',
      'payload': JSON.stringify(payload),
      'muteHttpExceptions': true
    };
    
    UrlFetchApp.fetch(url, options);
  } catch (e) {
    Logger.log('Webhook error: ' + e);
  }
}

/**
 * Add button-like formatting to status cells
 */
function formatStatusColumn() {
  var sheet = SpreadsheetApp.getActiveSheet();
  var data = sheet.getDataRange().getValues();
  
  for (var i = 1; i < data.length; i++) {
    var status = data[i][0];
    var cell = sheet.getRange(i + 1, 1);
    
    if (status === 'Approve') {
      cell.setBackground('#b7e1cd');
      cell.setFontWeight('bold');
      cell.setFontColor('#0d5302');
    } else if (status === 'Reject') {
      cell.setBackground('#f4c7c3');
      cell.setFontWeight('bold');
      cell.setFontColor('#a61c00');
    } else if (status === 'Review') {
      cell.setBackground('#fff2cc');
      cell.setFontWeight('normal');
      cell.setFontColor('#7f6000');
    }
  }
}

/**
 * On edit trigger - auto-format when status changes
 */
function onEdit(e) {
  var sheet = e.source.getActiveSheet();
  var range = e.range;
  
  // Check if edit was in column A (Status)
  if (range.getColumn() === 1 && range.getRow() > 1) {
    var value = range.getValue();
    
    if (value === 'Approve') {
      range.setBackground('#b7e1cd');
      range.setFontWeight('bold');
      range.setFontColor('#0d5302');
    } else if (value === 'Reject') {
      range.setBackground('#f4c7c3');
      range.setFontWeight('bold');
      range.setFontColor('#a61c00');
    } else if (value === 'Review') {
      range.setBackground('#fff2cc');
      range.setFontWeight('normal');
      range.setFontColor('#7f6000');
    }
  }
}


