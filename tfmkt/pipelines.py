import dateutil.parser
from inflection import parameterize


class CleanAppearancePipeline(object):

    def process_item(self, item, spider):
        """Takes appearances from the 'auto' spider and cleans them and converts
        them to appropriate types
        """
        # we just want to clean appearances for now
        if item.get('appearance') is not None:
            # clean stats
            stats = item['appearance']['stats']
            for key, value in stats.items():
                # minutes_played have an ending quote (for 'minutes')
                # we strip it out and convert it to int
                if (
                    key == 'minutes_played' or
                    key == 'substituted_on' or
                    key == 'substituted_off'
                ) and len(value) > 0:
                    value = int(value[:-1])
                # date comes as 'Apr 3, 2019', dateutil parser can deal with
                # this and other formats
                if key == 'date':
                    value = dateutil.parser.parse(value)
                # numeric statistics have empty strings inteand of 0s
                # we convert them here
                if type(value) == str and len(value) == 0:
                    value = 0
                # most of the appearance fields are ints in a string format
                # let's try to give them their right type
                if key == 'substituted_on':
                    print(type(value))
                elif type(value) == str:
                    try:
                        value = int(value)
                    except ValueError:
                        # if it's not a int, use a 'parameterized' version of
                        # the string
                        value = parameterize(value)

                stats[key] = value

            item['appearance']['stats'] = stats
            return item
        else:
            return item
