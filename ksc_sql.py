import pyodbc


mainQuery = """SELECT
                h.[nId],
                g.[wstrName],
                h.[strDnsName],
                hs.[status_id],
                hs.[status_mask],
                h.[wstrComment],
                h.[tmLastInfoUpdate],
                h.[strAddress],
                h.[nOsReleaseID],
                h.[nOsBuildNumber],
                hps.[tmAvbasesDate],
                h.[tmLastNagentConnected]
            FROM
                [!%DBNAME%!].[dbo].[Hosts] h
            JOIN
                [!%DBNAME%!].[dbo].[AdmGroups] g ON h.[nGroup] = g.[nId]
            JOIN
                [!%DBNAME%!].[dbo].[hst_host_status] hs ON h.[nId] = hs.[nId]
            LEFT JOIN (
                SELECT
                    nHostId,
                    tmAvbasesDate,
                    ROW_NUMBER() OVER (PARTITION BY nHostId ORDER BY tmAvbasesDate DESC) AS rn
                FROM
                    [!%DBNAME%!].[dbo].[hst_prdstates2]
            ) hps ON h.nId = hps.nHostId AND hps.rn = 1
            WHERE
                g.[wstrName] <> 'pseudohosts'"""
csvHeader = 'plant;id;group;name;status;descr;comment;last info update;address;OS version;OS build;database installed;last connect KSC;'
STATUS_CODES = {1: 'Система онлайн, но нет данных по NetworkAgent',
                2: 'Защита отключена',
                4: 'Антивирус не запущен',
                8: 'Обнаружено большое количество вредоносного ПО',
                16: 'Статус защиты отличается от настроек, заданных в политике',
                32: 'Антивирус не установлен',
                64: 'Сканирование системы давно не проводилось',
                128: 'Базы давно не обновлялись',
                256: 'NetworkAgent давно не подключался',
                512: 'Лицензия истекла',
                1024: 'Большое количество невылеченных объектов',
                2048: 'Необходима перезагрузка',
                4096: 'На системе есть несовместимое ПО',
                8192: 'На системе уязвимая ОС или ПО',
                16384: 'Давно не проводилась установка обновлений ОС',
                32768: 'Не удалось защифровать диск устройства',
                65536: 'Настройки мобильного устройства не соответствуют политикам безопасности',
                131072: 'Есть необработанные инциденты',
                262144: 'Данный статус установлен по команде HSDP',
                524288: 'На устройстве заканчивается дисковое пространство'}


class KSCConnector:
    '''Class to store info about each connection to KSC'''
    conn = None

    def __init__(self, srv, db, user, passwd, filename):
        self.server = srv
        self.database = db
        self.username = user
        self.password = passwd
        self.resultFile = filename

    def connect(self):
        '''Connect to KSC'''
        try:
            self.conn = pyodbc.connect('DRIVER={/opt/microsoft/msodbcsql18/lib64/libmsodbcsql-18.3.so.2.1};SERVER=' +\
                                       self.server + ';DATABASE=' + self.database + ';UID=' + self.username + ';PWD=' +\
                                       self.password + ';TrustServerCertificate=yes;')
        except Exception as err:
            logInfo(self.resultFile, err, 1)
            self.conn = None

        return self.conn

    def disconnect(self):
        '''Disconnect from KSC'''
        if self.conn is not None:
            conn.close()

KSClist = [KSCConnector('IP', 'bd_name', 'login', 'pass', 'file_name')]

def logInfo(serverName, errInfo, errCode, logPath='errors.txt'):
    '''Just write exception info to log file'''
    with open(logPath, 'a') as hfile:
        hfile.write(serverName + '\n' + str(errCode) + '\n' + str(errInfo) + '\n\n')

def getStatusString(mask):
    '''Convert status mask to status string description'''
    result = ''
    for code, descr in STATUS_CODES.items():
        if (code & mask) == 0:
            continue

        result += descr + ', '

    return result[:-2]

if __name__ == '__main__':
    # connect to each MS-SQL database one-by-one
    for ksc in KSClist:
        conn = ksc.connect()
        if conn is None:
            # TODO: notify admin
            continue

        # create cursor
        try:
            cursor = conn.cursor()
        except Exception as err:
            logInfo(ksc.resultFile, err, 2)
            ksc.disconnect()
            continue

        # execute SQL query and fetch results
        try:
            cursor.execute(mainQuery.replace('!%DBNAME%!', ksc.database))
            with open(ksc.resultFile + '.csv', 'w') as hfile:
                hfile.write(csvHeader + '\n')
                for i in cursor.fetchall():
                    # parse status code
                    if i[3] == 0:
                        i[3] = 'OK'
                    elif i[3] == 1:
                        i[3] = 'Error'
                    elif i[3] == 2:
                        i[3] = 'Warning'

                    # parse status mask
                    if i[3] != 'OK':
                        i[4] = getStatusString(i[4])
                    else:
                        i[4] = ''

                    # add plant name and write row to csv file
                    hfile.write(ksc.resultFile + ';' + ';'.join([str(x) for x in i]) + ';\n')
        except Exception as err:
            logInfo(ksc.resultFile, err, 3)
            cursor.close()
            ksc.disconnect()
            continue

        cursor.close()
        ksc.disconnect()
