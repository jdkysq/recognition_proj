# coding: utf-8
from BaseController import *
from lib.HoughCircleSplit import *
import numpy as np
import conf.Config as conf
import urllib2 as url
from scipy import ndimage
from lib.PreProcessing import *
from lib.imagemagick import detectAndGetImage
import urlparse
import json
import os

class HoughCircleSplitWithRotateController(BaseController):
	def execute(self):
		HoughCircleSplitWithRotateController.checkParams(self)
		if self.opType == 0:
			if not self.paperUrl:
				rawData = self.processUpFile("paper")
			else:
				# 从其他地方获取图片
				res = url.urlopen(self.paperUrl)
				rawData = res.read()
			img = cv2.imdecode(np.fromstring(rawData, np.uint8), cv2.IMREAD_COLOR)# IMREAD_COLOR
			# 二维码
			QRCodeData = {"paperW": 1476, "paperH": 1011, "id": -1, "pageNumber": 1}
			imgH, imgW, _ = img.shape
			img, qrcode = detectAndGetImage(img, self.imgFeature, "tmp/image/")
			if img is None or qrcode == -1:
				self.setResult([], STATUS_SCAN_ERROR)
				return
			queryData = urlparse.urlparse(qrcode).query
			queryData = urlparse.parse_qs(queryData)
			print queryData
			# ---test---
			queryData['paperType'] = 'a3'
			queryData['id'] = '111'
			queryData['pageNumber'] = 111
			# -----------
			if 'paperType' not in queryData or 'pageNumber' not in queryData or 'id' not in queryData:
				self.setResult([], STATUS_SCAN_ERROR)
				return
			QRCodeData['paperType'] = queryData['paperType']
			QRCodeData['pageNumber'] = queryData['pageNumber']
			QRCodeData['id'] = queryData['id']

			# 单开
			if QRCodeData['paperType'] in ["a4", "16k", "b5"]:
				QRCodeData["paperW"] = 1300
				QRCodeData["paperH"] = 2000
			# 双开
			else:
				QRCodeData["paperW"] = 1476
				QRCodeData["paperH"] = 1011
			originImg = img
			# img = filterBlue(img)
			if self.isMobile == -1:
				img = filterBlack(img)
				if imgW >= 2000:
					resizeW, resizeH = (int(imgW * 0.5), int(imgH * 0.5))
				else:
					resizeW, resizeH = (int(imgW * 0.8), int(imgH * 0.8))
				# 缩放至固定尺寸，方便调参
				# resizeW, resizeH = (int(self.paperW / 3.36), int(self.paperH / 3.46))# (1476, 1011) # 1300, 2000
				img = cv2.resize(img, (resizeW, resizeH))
				(circles, imgList) = circleSplit(img, QRCodeData["paperW"], QRCodeData["paperH"], scaleThresh = 1.0, showImg = False)
			else:
				# img = filterBlack(img, [0, 0, 0], [180, 255, 90])
				img = filterBlack(img)
				if imgW >= 2000:
					resizeW, resizeH = (int(imgW * 0.5), int(imgH * 0.5))
				else:
					resizeW, resizeH = (int(imgW * 0.8), int(imgH * 0.8))
				originImg = cv2.resize(originImg, (resizeW, resizeH))
				img = cv2.resize(img, (resizeW, resizeH))
				(circles, imgList) = circleSplitMobile(img, QRCodeData["paperW"], QRCodeData["paperH"], scaleThresh = 1.0, colorImg = originImg, showImg = False)
			if len(imgList) > 0 and self.opType == 0:
				# cv2.imwrite("resources/tmp/tmp.png", imgList[0])
				retval, buf = cv2.imencode(".jpg", imgList[0])
				if retval:
					with open("tmp/data/%s.qrdata" % QRCodeData['id'], "w") as qrfile:
						qrfile.write(json.dumps(queryData, ensure_ascii=False));
					if int(self.version[2]) >= 10:
						rawData = buf.tobytes()
					else:
						rawData = buf.tostring()
					self.set_header('Content-Type', 'image/jpeg')
					self.write(rawData)
					self.flush()
				else:
					self.setResult([], STATUS_ENCODE_ERROR)
			else:
				self.setResult([], STATUS_SCAN_ERROR)
		# 返回二维码数据
		if self.opType == 1:
			filename = "tmp/data/%s.qrdata" % self.qrid
			if os.path.isfile(filename):
				with open(filename, "r") as qrfile:
					qrdata = qrfile.readline()
				# os.remove(filename)
				self.setResult(qrdata, STATUS_OK)
			else:
				raise ErrorStatusException("qrid[%s] does not exit" % self.qrid, STATUS_PARAM_ERROR)

	@staticmethod
	def checkParams(self):
		opType = self.getIntArg("opType")
		if opType < 0:
			opType = 0 # 返回图片
		if opType != 0 and opType !=1:
			raise ErrorStatusException("opType must be a positive number(0: 返回图片, 1: 根据图片id返回二维码)", STATUS_PARAM_ERROR)
		self.opType = opType
		if opType == 0:
			self.isMobile = self.getIntArg("isMobile")
			self.imgFeature = self.getStrArg("imgFeature", "resources/qr.jpg")
			self.imgFeature = cv2.imread(self.imgFeature)
			if self.imgFeature is None:
				raise ErrorStatusException("imgFeature must be a valid resource name", STATUS_PARAM_ERROR)
			
			if not self.fileExist("paper"):
				self.paperUrl = self.getStrArg("paper")
			else:
				self.paperUrl = None
		if opType == 1:
			qrid = self.getStrArg("qrid")
			if qrid is None or qrid == "":
				raise ErrorStatusException("qrid must not be null", STATUS_PARAM_ERROR)
			self.qrid = qrid

