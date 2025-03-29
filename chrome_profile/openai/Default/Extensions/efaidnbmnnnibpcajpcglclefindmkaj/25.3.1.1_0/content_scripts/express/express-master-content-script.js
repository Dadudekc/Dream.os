/*************************************************************************
* ADOBE CONFIDENTIAL
* ___________________
*
*  Copyright 2015 Adobe Systems Incorporated
*  All Rights Reserved.
*
* NOTICE:  All information contained herein is, and remains
* the property of Adobe Systems Incorporated and its suppliers,
* if any.  The intellectual and technical concepts contained
* herein are proprietary to Adobe Systems Incorporated and its
* suppliers and are protected by all applicable intellectual property laws,
* including trade secret and or copyright laws.
* Dissemination of this information or reproduction of this material
* is strictly forbidden unless prior written permission is obtained
* from Adobe Systems Incorporated.
**************************************************************************/
class ExpressMaster{init(){this.loadContentScripts()}loadContentScripts(){const e=chrome.runtime.getURL("content_scripts/express/express-fte.js");return Promise.all([import(e)]).then((e=>{this.expressFte=e[0].default,this.expressFte.showFteIfEligible()}))}}const expressMaster=new ExpressMaster;expressMaster.init();