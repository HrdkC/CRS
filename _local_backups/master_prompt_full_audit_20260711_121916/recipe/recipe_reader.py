class RecipeReader:

    def __init__(self, plc_connection):
        self.plc = plc_connection

    def read_recipe(self, tag_list):
        return self.plc.read_tags(tag_list)