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


def apply_signature(job):
    # getting the image and signature file names.
    image_file, wm_file = job.data.split(':::')

    # loading the signature
    signature = Image.open(wm_file)
    signature, mode = _wm_mode(signature)

    # loading the image
    image = Image.open(image_file)
    image_format = image.format
    if 'RGB' not in image.mode:
        image = image.convert('RGB')

    # injecting signature
    signatureed = inject_wm(signature, image, mode)

    # saving the result
    image_filename, ext = os.path.splitext(image_file)
    target = os.path.join(image_filename + '_wm' + ext)

    if image.format == 'JPEG':
        try:
            signatureed.save(target, image.format, quality=95, optimize=1)
        except IOError:
            signatureed.save(target, image.format, quality=95)
    else:
        try:
            signatureed.save(target, image.format, optimize=1)
        except IOError:
            signatureed.save(target, image.format)

    return target


class FileFinder(threading.Thread):
    def __init__(self, root, queue):
        threading.Thread.__init__(self)
        self.root = root
        self.queue = queue

    def run(self):
        logger.debug('Looking for files in %r' % self.root)
        for root, dirs, files in os.walk(self.root):
            for file in files:
                name, ext = os.path.splitext(file)
                if ext.lower() != '.jpg' or name.endswith('_wm'):
                    continue
                path = os.path.join(root, file)
                self.queue.put(path)
                sys.stdout.write('+')
                sys.stdout.flush()


class Worker(threading.Thread):
    def __init__(self, queue, pool, signature, phose=False):
        threading.Thread.__init__(self)
        self.queue = queue
        self.phose = phose
        self.pool = pool
        self.signature = signature

    def run(self):
        while not self.queue.empty():
            path = self.queue.get()
            try:
                data = path + ':::' + self.signature
                if self.phose:
                    result = self.pool.execute(data)
                else:
                    result = apply_signature(FakeJob(data))

                sys.stdout.write('.')
                sys.stdout.flush()
            except Exception, e:
                logger.error(str(e))


def main():
    signature  = os.path.join(os.path.expanduser('~'), '.signature.jpg')
    if not os.path.exists(signature):
        signature = os.path.join(os.path.dirname(__file__), 'signature.jpg')

    parser = argparse.ArgumentParser(description='Sign some pictures.')

    parser.add_argument('pic', help="Directory or single picture.",
                        action='store')

    parser.add_argument('--signature',
                        help=("Signature file. If not given, will look at "
                              "~/.signature.jpg then fallback to the "
                              "included signature."),
                        default=signature)

    parser.add_argument('--debug', action='store_true', default=False,
                        help="Debug mode")

    parser.add_argument('--phose', action='store_true', default=False,
                        help="Use Powerhose")

    parsed = parser.parse_args()

    import logging

    if parsed.debug:
        level = logging.DEBUG
    else:
        level = logging.INFO

    logger.setLevel(level)
    ch = logging.StreamHandler()

    if parsed.debug:
        ch.setLevel(level)
    else:
        ch.setLevel(level)

    formatter = logging.Formatter('[%(asctime)s][%(name)s] %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    phose_logger = logging.getLogger('powerhose')
    phose_logger.addHandler(ch)

    queue = Queue.Queue()

    if not os.path.exists(parsed.pic):
        print("%r does not seem to exist" % parsed.pic)
        sys.exit(1)

    logger.info('Using signature file %r' % parsed.signature)

    # looking for files
    if os.path.isdir(parsed.pic):
        logger.info('Looking for files in %r' % parsed.pic)
        finder = FileFinder(parsed.pic, queue)
        finder.start()
        time.sleep(.1)      # give it a chance to start
    else:
        finder = None
        queue.put(parsed.pic)

    # run the cluster
    if parsed.phose and finder is not None:
        from powerhose import get_cluster
        from powerhose.client import Pool
        pool = Pool(timeout=30.)
        logger.debug('Starting the PowerHose cluster')
        cluster = get_cluster('signpic.sign.apply_signature', background=True)
        cluster.start()
        time.sleep(1.)
    else:
        if parsed.phose:
            logger.warning('Not using --phose for a single picture!')
        pool = None

    try:
        workers = [Worker(queue, pool, parsed.signature,
                          parsed.phose) for i in range(10)]

        for worker in workers:
            worker.start()

        if finder is not None:
            finder.join()

        for worker in workers:
            worker.join()
    finally:
        if parsed.phose:
            cluster.stop()

    sys.stdout.write('Done.\n')


if __name__ == '__main__':
    pic = sys.argv[1]
    signature = os.path.join(os.path.dirname(__file__), 'signature.jpg')
    j = FakeJob('%s:::%s' % (pic, signature))
    print apply_signature(j)
