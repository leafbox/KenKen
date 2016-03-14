#Imports

from google.appengine.api import users
from google.appengine.ext import ndb

import cgi, os, math, sys, re, string, os

from time import strftime, localtime
import datetime

import jinja2
import webapp2

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

#end Imports

#Start Functions

def get_shift_date():
	# Date boundary is 4 am PST
	return datetime.datetime.utcnow() - datetime.timedelta(hours=8)

def is_am():
	return (datetime.datetime.utcnow() + datetime.timedelta(hours=8)).hour < 12

def validate_CashFormItem(cashItem):
		if cashItem.isdigit():
			return True
		else:
			return False

def get_form_details(form_data):
	dropType = form_data.request.get('dropType')
	author = form_data.request.get('workerName')
	creditCardSales = form_data.request.get("creditCardSales")
	cashSales = form_data.request.get("cashSales")
	cardTips = form_data.request.get("creditCardTips")
	cashTips = form_data.request.get("cashTips")
	notesContent = form_data.request.get("notesContent")
	return dropType, author, creditCardSales, cashSales, cardTips, cashTips, notesContent

#Start Main Program Elements

DEFAULT_CASHDROP_NAME = 'DEFAULT_CASHDROP'

def cashdrop_key(cashdrop_name=DEFAULT_CASHDROP_NAME):
    return ndb.Key('DEFAULT_CASHDROP', cashdrop_name)

class CashDrop(ndb.Model):
		dropType = ndb.StringProperty(indexed=True)
		author = ndb.StringProperty(indexed=True)
		creditCardSales = ndb.IntegerProperty()
		cashSales = ndb.IntegerProperty()
		creditCardTips = ndb.IntegerProperty()
		cashTips = ndb.IntegerProperty()
		totalSales = ndb.IntegerProperty()
		totalTips = ndb.IntegerProperty()
		tipRate = ndb.FloatProperty()
		barTips = ndb.FloatProperty()
		hostTips = ndb.FloatProperty()
		kitchenTips = ndb.FloatProperty()
		serverTips = ndb.FloatProperty()
		cashInEnvelope = ndb.FloatProperty()
		notesContent = ndb.StringProperty(indexed=False)

		dateOnEnvelope = ndb.StringProperty(indexed=True)
		date = ndb.DateTimeProperty(auto_now_add=True)

		@classmethod
		def query_book(cls, ancestor_key):
			return cls.query(ancestor=ancestor_key).order(-cls.date)

class MainPage(webapp2.RequestHandler):

  def get(self):

  	template_values = { 'validCreditCardSalesEntry' : True,
  	'validCashSalesEntry' : True,
  	'validCreditCardTipsEntry' : True,
  	'validCashTipsEntry' : True,
  	'dropType' : "",
  	'author' : "",
  	'creditCardSales' : "",
  	'cashSales' : "",
  	'cardTips' : "",
  	'cashTips' : "",
  	'notesContent' : ""
  	}

  	template = JINJA_ENVIRONMENT.get_template('templates/index.html')
  	self.response.write(template.render(template_values))

class tipsCalc(webapp2.RequestHandler):

	def post(self):

		#Get Data From Form
		dropType, author, creditCardSales, cashSales, cardTips, cashTips, notesContent = get_form_details(self)

		#Validate Form

		validCreditCardSalesEntry = validate_CashFormItem(creditCardSales)
		validCreditCashSalesEntry = validate_CashFormItem(cashSales)
		validCreditCardTipsEntry = validate_CashFormItem(cardTips)
		validCreditCashTipsEntry = validate_CashFormItem(cashTips)

		#If Valid Form GO

		if validCreditCardSalesEntry and validCreditCashSalesEntry and validCreditCardTipsEntry and validCreditCashTipsEntry:

			now = get_shift_date() #Get California Time

			totalSales = float(creditCardSales) + float(cashSales)
			totalTips = float(cardTips) + float(cashTips)
			cashInEnvelope = float(cashSales) - float(cardTips)

			tipRate = round(((totalTips / totalSales) * 100),2) #convert to percentage + round to 2 decimals

			tipSplit = False;
			barTips = 0
			hostTips = 0
			kitchenTips = 0
			serverTips = 0

			if dropType == "Floor-Lunch":
						tipSplit = True;
						barTips = totalTips * .0
						hostTips = totalTips * .0
						kitchenTips = totalTips * .30
						serverTips = totalTips * .70

			if dropType == "Floor":
					if now.weekday() == 6:
							tipSplit = True;
							barTips = totalTips * .12
							hostTips = totalTips * .0
							kitchenTips = totalTips * .23
							serverTips = totalTips * .65
					else:
							tipSplit = True;
							barTips = totalTips * .10
							hostTips = totalTips * .15
							kitchenTips = totalTips * .20
							serverTips = totalTips * .55

			cashdrop_name = DEFAULT_CASHDROP_NAME

			cashdrop = CashDrop(parent=cashdrop_key(cashdrop_name))

			cashdrop.dropType = dropType

			cashdrop.author = author

			cashdrop.creditCardSales = int(creditCardSales)
			cashdrop.cashSales = int(cashSales)
			cashdrop.creditCardTips = int(cardTips)
			cashdrop.cashTips = int(cashTips)

			cashdrop.totalSales = int(totalSales)
			cashdrop.totalTips = int(totalTips)

			cashdrop.tipRate = tipRate
			cashdrop.barTips = barTips
			cashdrop.hostTips = hostTips
			cashdrop.kitchenTips = kitchenTips
			cashdrop.serverTips = serverTips

			cashdrop.cashInEnvelope = cashInEnvelope

			cashdrop.dateOnEnvelope = now.strftime('%A %m/%d/%Y')

			cashdrop.notesContent = notesContent

			#Query DB for existing Record:

			cashdrop_name = 'DEFAULT_CASHDROP'
			ancestor_key = ndb.Key("DEFAULT_CASHDROP", cashdrop_name or "*notitle*")

			cashdrops = CashDrop.query_book(ancestor_key).filter(CashDrop.dropType == cashdrop.dropType, CashDrop.dateOnEnvelope == cashdrop.dateOnEnvelope).fetch()

			existsFlag = False

			#update DB for Entry
			if cashdrops:
				ndb.delete_multi([x.key for x in cashdrops])
				cashdrop.put()
				existsFlag = True
			else:
				cashdrop.put()
				existsFlag = False

			template_values = {
				'existsFlag' : existsFlag,
				'tipSplit' : tipSplit,
				'date' : cashdrop.dateOnEnvelope,
				'author' : cashdrop.author,
				'dropType': cashdrop.dropType,
				'creditCardSales' : cashdrop.creditCardSales,
				'cashSales' : cashdrop.cashSales,
				'creditCardTips' : cashdrop.creditCardTips,
				'cashTips' : cashdrop.cashTips,
				'totalSales' : cashdrop.totalSales,
				'totalTips' : cashdrop.totalTips,
				'tipRate' : cashdrop.tipRate,
				'barTips' : cashdrop.barTips,
				'hostTips' : cashdrop.hostTips,
				'kitchenTips' : cashdrop.kitchenTips,
				'serverTips' : cashdrop.serverTips,
				'cashInEnvelope' : cashdrop.cashInEnvelope,
				'notesContent' : cashdrop.notesContent
        }

			template = JINJA_ENVIRONMENT.get_template('templates/tipcalc.html')
			self.response.write(template.render(template_values))

		else:
			#generate form to show invalid data

			validCreditCreditCardSalesEntry = validate_CashFormItem(creditCardSales)
			validCashSalesEntry = validate_CashFormItem(cashSales)
			validCreditCardTipsEntry = validate_CashFormItem(cardTips)
			validCashTipsEntry = validate_CashFormItem(cashTips)

			template_values = {
				'validCreditCardSalesEntry' : validCreditCardSalesEntry,
				'validCashSalesEntry' : validCashSalesEntry,
				'validCreditCardTipsEntry' : validCreditCardTipsEntry,
				'validCashTipsEntry' : validCashTipsEntry,
				'dropType' : dropType,
				'author' : author,
				'creditCardSales' : creditCardSales,
				'cashSales' : cashSales,
				'cardTips' : cardTips,
				'cashTips' : cashTips,
				'notesContent' : notesContent,
	    }

			template = JINJA_ENVIRONMENT.get_template('templates/index.html')
			self.response.write(template.render(template_values))

class viewDrops(webapp2.RequestHandler):
	def get(self):

		cashdrop_name = 'DEFAULT_CASHDROP'
		ancestor_key = ndb.Key("DEFAULT_CASHDROP", cashdrop_name or "*notitle*")
		cashdrops = CashDrop.query_book(ancestor_key).fetch()
		#cashdrops = CashDrop.query_book(ancestor_key).filter(CashDrop.dropType == 'Floor', CashDrop.creditCardSales == 4000).fetch()

		template_values = {
				'cashdrops': cashdrops,
        }

		template = JINJA_ENVIRONMENT.get_template('templates/viewdrops.html')
		self.response.write(template.render(template_values))

class dashBoard(webapp2.RequestHandler):
	def get(self):

		cashdrop_name = 'DEFAULT_CASHDROP'
		ancestor_key = ndb.Key("DEFAULT_CASHDROP", cashdrop_name or "*notitle*")
		cashdrops = CashDrop.query_book(ancestor_key).fetch()

		template_values = {
				'cashdrops': cashdrops,
        }

		template = JINJA_ENVIRONMENT.get_template('templates/dashboard.html')
		self.response.write(template.render(template_values))

app = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/tipsCalc', tipsCalc),
    ('/viewDrops', viewDrops),
    ('/dashBoard', dashBoard),

], debug=True)