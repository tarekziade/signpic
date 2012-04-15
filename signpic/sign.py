# inspired from http://www.turboradness.com/watermark-your-images-with-python
import os
import sys
import Queue
import threading
import time
import argparse

import Image, ImageChops, ImageOps, ImageEnhance


from signpic import logger


_OPACITY = 50
_POSITION = 3


class FakeJob(object):
    def __init__(self, data):
        self.data = data


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
        wm = _resize_wm(wm, wm.size, im.size)
        wmbuffer = 1

    if wm_mode == "screen":
        water_marked = screen_mode(im, wm, wmbuffer)

    elif wm_mode == "over":
        water_marked = over_mode(im, wm, wmbuffer)

    return water_marked


def _resize_wm(wm, wmsize, imsize):
    if imsize[0] < wmsize[0]:
        #Image X res is larger than its Y res.
        divVal = float(imsize[0]) / float(wmsize[0])
        newWmXres = int(round(float(wmsize[0] * divVal)))
        newWmYres = int(round(float(wmsize[1] * divVal)))
        wm = wm.resize((newWmXres,newWmYres), Image.ANTIALIAS)
    else:
        divVal = float(imsize[1]) / float(wmsize[1])
        newWmXres = int(round(float(wmsize[0] * divVal)))
        newWmYres = int(round(float(wmsize[1] * divVal)))
        wm = wm.resize((newWmXres,newWmYres), Image.ANTIALIAS)

    return wm


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
    image_file, wm_file = job.data.split(':::')

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


class FileFinder(threading.Thread):
    def __init__(self, root, queue):
        threading.Thread.__init__(self)
        self.root = root
        self.queue = queue

    def run(self):
        for root, dirs, files in os.walk(self.root):
            for file in files:
                name, ext = os.path.splitext(file)
                if ext.lower() != '.jpg' or name.endswith('_wm'):
                    continue
                path = os.path.join(root, file)
                self.queue.put(path)


class Worker(threading.Thread):
    def __init__(self, queue, pool, watermark, phose=False):
        threading.Thread.__init__(self)
        self.queue = queue
        self.phose = phose
        self.pool = pool
        self.watermark = watermark

    def run(self):
        while not self.queue.empty():
            path = self.queue.get()
            logger.info('Sending %s' % path)
            try:
                data = path + ':::' + self.watermark
                if self.phose:
                    result = self.pool.execute(data)
                else:
                    result = apply_watermark(FakeJob(data))
                logger.info('Result: ' + result)

            except Exception:
                logger.info('Failed for %s' % path)


def main():
    parser = argparse.ArgumentParser(description='Sign some pictures.')

    parser.add_argument('--debug', action='store_true', default=False,
                        help="Debug mode")

    parser.add_argument('--phose', action='store_true', default=False,
                        help="Use Powerhose")

    parser.add_argument('pic', help="Directory or single picture.")

    args = parser.parse_args()

    import logging
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()

    if args.debug:
        ch.setLevel(logging.DEBUG)
    else:
        ch.setLevel(logging.INFO)

    formatter = logging.Formatter('[%(asctime)s][%(name)s] %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    queue = Queue.Queue()

    # look for files
    finder = FileFinder(args.pic, queue)
    finder.start()

    # run the cluster
    if args.phose:
        from powerhose import get_cluster
        from powerhose.client import Pool

        pool = Pool()
        logger.info('Starting the cluster')
        cluster = get_cluster('signpic.sign.apply_watermark', background=True)
        cluster.start()
        time.sleep(2.)
    else:
        pool = None

    watermark = os.path.join(os.path.dirname(__file__), 'signature.jpg')
    try:
        workers = [Worker(queue, pool, watermark,
                          args.phose) for i in range(10)]

        for worker in workers:
            worker.start()

        finder.join()
        for worker in workers:
            worker.join()
    finally:
        if args.phose:
            cluster.stop()


if __name__ == '__main__':
    pic = sys.argv[1]
    signature = os.path.join(os.path.dirname(__file__), 'signature.jpg')
    j = FakeJob('%s:::%s' % (pic, signature))
    print apply_watermark(j)
