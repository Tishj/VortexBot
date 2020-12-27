import PIL.ImageOps 
try:
	from PIL import Image,ImageEnhance, ImageFilter
except ImportError:
	import Image
import pytesseract

def get_string_from_image(filename):
#	image = open_eps(filename)
	image = Image.open(filename)
	start, end = True, True
	x, _ = image.size
	word_span_start, word_span_end = 0, x - 1
	print(word_span_start, word_span_end)
	for i in range(x):
		print(word_span_start, word_span_end)
		if start and word_span_start < word_span_end and image.getpixel((word_span_start, 7)) < (225,225,225):
			word_span_start += 1
		else:
			start = False
		if end and word_span_end > word_span_start and image.getpixel((word_span_end, 7)) < (225,225,225):
			word_span_end -= 1
		else:
			end = False
		if end == False and start == False:
			break
	image = image.crop((word_span_start - 5, 0, word_span_end + 5, 18))
	print(word_span_start, word_span_end)
	width, height = image.size
	image = image.resize((width * 4, height * 4), PIL.Image.NEAREST)
	try:
		image = PIL.ImageOps.grayscale(image)
	except:
		pass
#	image = image.filter(PIL.ImageFilter.GaussianBlur(2.9))
	image = ImageEnhance.Contrast(image).enhance(2)
	image = image.point(lambda i: i > 235 and 255)
	image = PIL.ImageOps.invert(image)
	image.show()
	config = "--psm 6 -c tessedit_char_whitelist=0123456789KMT" #magby
	text = pytesseract.image_to_string(image, config=config)
	return text

text = get_string_from_image("/c/users/thijs/desktop/codam/vortexbot/screenshot.PNG")

print(text)