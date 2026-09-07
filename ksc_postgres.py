# -*- coding: utf-8 -*-

import psycopg2

mainQuery = '''SELECT
                h."nId",
                g."wstrName",
                h."strDnsName",
                hs."status_id",
                hs."status_mask",
                h."wstrComment",
                h."tmLastInfoUpdate",
                h."strAddress",
                h."nOsReleaseID",
                h."nOsBuildNumber",
                COALESCE(TO_CHAR(hps."tmAvbasesDate", 'YYYY-MM-DD HH24:MI:SS'), '—') AS "tmAvbasesDate",
                h."tmLastNagentConnected"
            FROM
                public."Hosts" h
            JOIN
                public."AdmGroups" g ON h."nGroup" = g."nId"
            JOIN
                public."hst_host_status" hs ON h."nId" = hs."nId"
            LEFT JOIN (
                SELECT
                    "nHostId",
                    "tmAvbasesDate",
                    ROW_NUMBER() OVER (
                        PARTITION BY "nHostId"
                        ORDER BY
                            CASE WHEN "tmAvbasesDate" IS NOT NULL THEN 0 ELSE 1 END,
                            "tmAvbasesDate" DESC
                    ) AS rn
                FROM
                    public."hst_prdstates2"
            ) hps ON h."nId" = hps."nHostId" AND hps.rn = 1
            WHERE
                g."wstrName" <> 'pseudohosts';'''

csvHeader = 'plant;id;group;name;status;descr;comment;last info update;address;OS version;OS build;database installed;last connect KSC;'
STATUS_CODES = {1: 'Система онлайн, но нет данных NetworkAgent',
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
                32768: 'Не удалось зашифровать диск устройства',
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
            self.conn = psycopg2.connect(
                dbname=self.database,
                user=self.username,
                password=self.password,
                host=self.server,
                port=5432  # Порт PostgreSQL по умолчанию
            )
        except Exception as err:
            self.log_info(err, 1)
            self.conn = None

        return self.conn

    def disconnect(self):
        '''Disconnect from KSC'''
        if self.conn is not None:
            self.conn.close()

    def log_info(self, err_info, err_code):
        '''Just write exception info to log file'''
        with open(self.resultFile, 'a', encoding='utf-8') as hfile:
            hfile.write(f"{self.server}\n{err_code}\n{err_info}\n\n")

def logInfo(serverName, errInfo, errCode, logPath='errors.txt'):
    '''Just write exception info to log file'''
    with open(logPath, 'a', encoding='utf-8') as hfile:
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
    KSClist = [KSCConnector('IP', 'db_name', 'login', 'pass', 'file_name')]

    # Connect to each PostgreSQL database one-by-one
    for ksc in KSClist:
        conn = ksc.connect()
        if conn is None:
            # TODO: notify admin
            continue

        # Create cursor
        try:
            cursor = conn.cursor()
        except Exception as err:
            ksc.log_info(err, 2)
            ksc.disconnect()
            continue

        # Execute SQL query and fetch results
        try:
            cursor.execute(mainQuery)
            with open(ksc.resultFile + '.csv', 'w', encoding='utf-8') as hfile:
                hfile.write(csvHeader + '\n')
                for i in cursor.fetchall():
                    #print (i)
                    # Parse status code
                    status = i[3]
                    if status == 0:
                        status = 'OK'
                    elif status == 1:
                        status = 'Error'
                    elif status == 2:
                        status = 'Warning'

                    # Parse status mask
                    status_descr = ''
                    if status != 'OK':
                        status_descr = getStatusString(i[4])

                    # Add plant name and write row to CSV file
                    row = [ksc.resultFile] + [str(x) for x in i[:3]] + [status, status_descr] + [str(x) for x in i[5:]]
                    hfile.write(';'.join(row) + ';\n')
        except Exception as err:
            ksc.log_info(err, 3)
            cursor.close()
            ksc.disconnect()
            continue

        cursor.close()
