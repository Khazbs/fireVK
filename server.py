import tornado.ioloop
import tornado.web
import requests
import json
import urllib.request
import urllib.parse
import urllib.error
import http.client

ss = json.load(open("ss.json", "r"))


class HomepageHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("./frontend/index.html")


class CognitiveHandler(tornado.web.RequestHandler):
    def post(self):
        args = dict(self.request.arguments)
        if "url" not in args.keys():
            self.set_status(400, "Parameter 'url' not specified")
            self.finish()
            return
        url = args["url"][0].decode("utf-8")
        headers = {
            # Request headers
            'Content-Type': 'application/json',
            'Ocp-Apim-Subscription-Key': ss["MS_CV_token"],
        }
        params = urllib.parse.urlencode({
            # Request parameters
            'visualFeatures': 'Tags, Description',
        })
        conn = http.client.HTTPSConnection('westus.api.cognitive.microsoft.com')
        conn.request("POST", "/vision/v1.0/analyze?%s" % params, json.dumps({"url": url}), headers)
        response = conn.getresponse()
        obj = json.loads(response.read().decode("utf-8"))
        conn.close()
        # print(obj)
        s = "With %.2f" % (obj["description"]["captions"][0]["confidence"] * 100) + "% chance this is " + obj["description"]["captions"][0]["text"] + "\n"
        if len(obj["tags"]):
            s += "Related tags: " + ", ".join([x["name"] for x in obj["tags"]])
        self.write(json.dumps({"desc_text": s}))


class PhotopageHandler(tornado.web.RequestHandler):
    def get(self):
        args = dict(self.request.arguments)
        try:
            lat = float((args["lat"][0].decode("utf-8") if "lat" in args.keys() else ""))
            long = float((args["long"][0].decode("utf-8") if "long" in args.keys() else ""))
            if "mode" in args.keys():
                mode = args["mode"][0].decode("utf-8")
                if mode == "fresh":
                    mode = "Fresh photos"
                    sort = "&sort=0"
                elif mode == "hot":
                    mode = "Hot photos"
                    sort = "&sort=1"
                else:
                    raise ValueError
            else:
                mode = "Fresh photos"
                sort = ""
            count = 100
            page = int((args["page"][0].decode("utf-8") if "page" in args.keys() else 0))
            if page < 0:
                raise ValueError
            mode_link = "../go?lat={}&long={}".format(lat, long) + ("&page=" + str(page) if "page" in args.keys() else "") + "&mode=" + ("fresh" if mode == "Hot photos" else "hot")
            if page > 0:
                prev_page_link = "../go?lat={}&long={}".format(lat, long) + "&page=" + str(page - 1) + ("&mode=" + args["mode"][0].decode("utf-8") if "mode" in args.keys() else "")
                prev_page_html = '<a href="{}" title="Jump to previous page"><button class="w3-btn glider-right">&lt;</button></a>'.format(prev_page_link)
            else:
                prev_page_html = ""
            next_page_link = "../go?lat={}&long={}".format(lat, long) + "&page=" + str(page + 1) + ("&mode=" + args["mode"][0].decode("utf-8") if "mode" in args.keys() else "")
            offset = page * count
        except ValueError:
            self.render("./frontend/error.html", explanation_text="Your query is invalid. Please make sure you have provided all of the required parameters with valid values.")
        else:
            response = requests.get("https://api.vk.com/method/photos.search?v=5.63&lat={}&long={}{}&count={}&offset={}&access_token={}".format(
                lat, long, sort, count, offset, ss["VK_token"]))
            obj = json.loads(response.text)
            photo_html = ""
            if "response" in obj.keys():
                photos_list = list(obj["response"]["items"])
                for photo in photos_list:
                    max_link = "../misc/placeholder.png"
                    for res in [2560, 1280, 807, 604, 130, 75]:
                        if "photo_" + str(res) in photo.keys():
                            max_link = photo["photo_" + str(res)]
                            break
                    exp_link = "../misc/placeholder.png"
                    for res in [807, 604, 130, 75]:
                        if "photo_" + str(res) in photo.keys():
                            exp_link = photo["photo_" + str(res)]
                            break
                    img_link = "../misc/placeholder.png"
                    for res in [604, 130, 75]:
                        if "photo_" + str(res) in photo.keys():
                            img_link = photo["photo_" + str(res)]
                            break
                    full_id = str(photo["owner_id"]) + "_" + str(photo["id"])
                    photo_html += '<div id={full_id} style="cursor: zoom-in;" data-expres="{exp_link}" data-maxres="{max_link}" onclick="expand(\'{full_id}\')"class="grid-item" style="display: inline-block;"><img width="200" src="{img_link}" /></div>'.format(exp_link=exp_link, full_id=full_id, max_link=max_link, img_link=img_link)
                self.render("./frontend/photo.html", lat_coor=lat, long_coor=long, prev_page_html=prev_page_html, next_page=next_page_link, page_no=page, mode_link=mode_link, mode_text=mode, photo_html=photo_html)
            else:
                self.write(response.text)


def make_app():
    return tornado.web.Application([
        (r"/", HomepageHandler),
        (r"/go", PhotopageHandler),
        (r"/cognitive", CognitiveHandler),
        (r"/misc/(.*)", tornado.web.StaticFileHandler, {'path': 'misc'})
    ], debug=True)


if __name__ == "__main__":
    app = make_app()
    app.listen(8888)
    tornado.ioloop.IOLoop.current().start()
