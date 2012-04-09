# inspired from http://www.turboradness.com/watermark-your-images-with-python
import os
import Image, ImageChops, ImageOps, ImageEnhance

_OPACITY = 50
_POSITION = 3


def _wm_mode(image):
    if 'RGB' not in image.mode:
        image = image.convert('RGB')
        return image, "screen"

    if len(image.mode) == 4:
        image_copy = image.copy()
        mask = image_copy.split()[-1]
        image_copy.putalpha(mask)
        return image_copy, "over"

    if len(image.mode) == 3:
        return image, "screen"

    raise NotImplementedError()


def inject_wm(wm, im, wm_mode):
    wmbuffer = 10

    if wm.size[0] > im.size[0] or wm.size[1] > im.size[1]:
        wm = _resize_wm(wm, wm.size, image.size)
        wmbuffer = 1

    if wm_mode == "screen":
        water_marked = screen_mode(im, wm, wmbuffer)

    elif wm_mode == "over":
        water_marked = over_mode(im, wm, wmbuffer)

    return water_marked


def screen_mode(im, wm, wmbuffer):

    imsize = im.size
    wmsize = wm.size
    brightness = float(_OPACITY) / 100
    brightval = int(round(255 * brightness))
    wm_pos = _wm_pos(wmbuffer, imsize, wmsize)
    black_bg = Image.new('RGB', imsize, (0, 0, 0) )
    black_bg.paste(wm, wm_pos)
    darkener = Image.new('RGB', imsize, (brightval, brightval, brightval) )
    darkened_fit_wm = ImageChops.multiply(black_bg, darkener)
    return ImageChops.screen(darkened_fit_wm, im)


def over_mode(im, wm, wmbuffer):
    imsize = im.size
    wmsize = wm.size
    wm_pos = _wm_pos(wmbuffer, imsize, wmsize)
    wm_alpha = wm.split()[-1]

    if _OPACITY != 100:
        brightness = float(_OPACITY) / 100
        wm_alpha = ImageEnhance.Brightness(wm_alpha).enhance(brightness)

    black_bg = Image.new('RGBA', imsize, (0, 0, 0, 0))
    black_bg.paste(wm, wm_pos, wm_alpha)
    obc = black_bg.copy()
    obcmask = obc.split()[-1]
    out = ImageChops.composite(black_bg, im, obcmask)
    out.convert('RGB')
    return out


def _wm_pos(wmbuffer, imsize, wmsize ):
    imsizeX = imsize[0]
    imsizeY = imsize[1]
    wmsizeX = wmsize[0]
    wmsizeY = wmsize[1]
    xpos = imsizeX - wmbuffer - wmsizeX
    ypos = imsizeY - wmbuffer - wmsizeY
    return xpos, ypos


def apply_watermark(job):
    # getting the image and watermark file names.
    image_file, wm_file = job.data.split()

    # loading the watermark
    watermark = Image.open(wm_file)
    watermark, mode = _wm_mode(watermark)

    # loading the image
    image = Image.open(image_file)
    image_format = image.format
    if 'RGB' not in image.mode:
        image = image.convert('RGB')

    # injecting watermark
    watermarked = inject_wm(watermark, image, mode)

    # saving the result
    image_filename, ext = os.path.splitext(image_file)
    target = os.path.join(image_filename + '_wm' + ext)

    if image.format == 'JPEG':
        try:
            watermarked.save(target, image.format, quality=95, optimize=1)
        except IOError:
            watermarked.save(target, image.format, quality=95)

    else:
        try:
            watermarked.save(target, image.format, optimize=1)
        except IOError:
            watermarked.save(target, image.format)

    return target


if __name__ == '__main__':
    from powerhose.job import Job

    j = Job('IMGP1079.jpg watermark.jpg')
    print apply_watermark(j)

