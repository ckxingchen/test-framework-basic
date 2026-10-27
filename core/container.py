class GlobalManager:
    """全局变量变量"""
    global_dict = {}

    @classmethod
    def init_global(cls):
        cls.global_dict = dict()

    @classmethod
    def set_value(cls, name, value):
        cls.global_dict[name] = value

    @classmethod
    def get_value(cls, name):
        try:
            return cls.global_dict[name]
        except KeyError as e:
            print("获取全局变量名称：{}不存在：{}".format(name, e))
            return None

    @classmethod
    def clear(cls):
        cls.global_dict.clear()


class LocalManager:
    """局部变量"""
    local_dict = {}

    @classmethod
    def init_local(cls):
        cls.local_dict = dict()

    @classmethod
    def set_value(cls, name, value):
        cls.local_dict[name] = value

    @classmethod
    def get_value(cls, name):
        try:
            return cls.local_dict[name]
        except KeyError as e:
            print("获取局部变量名称：{}不存在：{}".format(name, e))
            return None

    @classmethod
    def clear(cls):
        cls.local_dict.clear()

if __name__ == "__main__":
    g = GlobalManager()
    res = g.get_value('driver')
    print(res)
