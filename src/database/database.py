#########################################################################
#                                                                       #
#                       Grupo Developers                                #
#                                                                       #
#                GNU General Public License v3                          #
#                                                                       #
#########################################################################

import MySQLdb

from decouple import config

from messages_controller import MessagesController, extract_chat_object, extract_user_object
from models.chat import Chat
from models.user import User


class Database():
    def __init__(self):
        db = MySQLdb.connect(passwd=config("DB_PASSWORD"), db=config("DB_NAME"),
                             user=config("DB_USER"), host=config("DB_HOST"))
        self.messages_controller = MessagesController()
        self.cursor = db.cursor()
        self.db = db
        self.chats_saved = []
        self.users_saved = []

    def update(self, telegram_message):
        chat = extract_chat_object(telegram_message)
        user = extract_user_object(telegram_message)

        if chat not in self.chats_saved:
            if not self.find_chat(chat.chat_id):
                self.insert_chat(chat)
                self.chats_saved.append(chat)

        if user not in self.users_saved:
            if not self.find_user(user.telegram_id):
                self.insert_user(user)
                self.users_saved.append(user)

        if len(self.chats_saved) > 3:
            self.chats_saved = []
        if len(self.users_saved) > 10:
            self.users_saved = []

    def find_chat(self, chat_id):
        query = """
                SELECT
                    a.id,
                    a.chat_id,
                    a.title,
                    a.chat_type
                FROM
                    chats AS a
                WHERE
                    a.chat_id=%s;
                """

        if self.cursor.execute(query, (chat_id,)) == 0:
            return None

        chat_db = self.cursor.fetchone()
        return Chat(
            chat_id=chat_db[1],
            title=chat_db[2],
            chat_type=chat_db[3]
        )

    def find_user(self, telegram_id):
        query = """
                SELECT
                    a.id,
                    a.telegram_id,
                    a.is_bot,
                    a.first_name,
                    a.last_name,
                    a.username
                FROM
                    users AS a
                WHERE
                    a.telegram_id=%s;
                """

        if self.cursor.execute(query, (telegram_id,)) == 0:
            return None

        user_db = self.cursor.fetchone()
        return User(
            telegram_id=user_db[1],
            is_bot=user_db[2],
            first_name=user_db[3],
            last_name=user_db[4],
            username=user_db[5]
        )

    def insert_chat(self, chat):
        query = """
                INSERT INTO
                    chats (chat_id, title, chat_type)
                VALUES
                    (%s, %s, %s);
                """
        print(chat.chat_id, chat.title, chat.chat_type)
        self.cursor.execute(query, (chat.chat_id, chat.title, chat.chat_type,))
        self.db.commit()

    def insert_user(self, user):
        query = """
                INSERT INTO
                    users (telegram_id, is_bot, first_name, last_name, username)
                VALUES
                    (%s, %s, %s, %s, %s);
                """
        self.cursor.execute(query,
                            (user.telegram_id, user.is_bot, user.first_name,
                             user.last_name, user.username,))
        self.db.commit()

    def find_experience_points(self, user_telegram_id, chat_id):
        query = """
                SELECT
                    a.experience_points
                FROM
                    experiences AS a
                WHERE
                    a.user_telegram_id = %s AND
                    a.chat_id = %s;
                """

        self.cursor.execute(query, (user_telegram_id, chat_id,))
        experience_points = self.cursor.fetchone()
        return experience_points[0] if experience_points else 0

    def add_user_experience(self, user_telegram_id, experience, chat_id):
        current_experience_points = self.find_experience_points(
            user_telegram_id, chat_id)
        new_experience_points = current_experience_points + experience
        if current_experience_points == 0:
            query = """
                    INSERT INTO
                        experiences (experience_points, user_telegram_id, chat_id)
                    VALUES
                        (%s, %s, %s);
                    """
        else:
            query = """
                    UPDATE
                        experiences
                    SET
                        experience_points = %s
                    WHERE
                        user_telegram_id = %s AND
                        chat_id = %s;
                    """

        self.cursor.execute(query, (experience_points, user_telegram_id, chat_id,))
        self.db.commit()

    def get_experiences(self, chat_id, amount=10):
        query = """
                SELECT
                    u.first_name,
                    u.last_name,
                    u.username,
                    e.experience_points
                FROM
                    experiences AS e
                INNER JOIN
                    chats AS c ON e.chat_id = c.chat_id
                INNER JOIN
                    users AS u ON e.user_telegram_id = u.telegram_id
                WHERE
                    e.chat_id = {chat_id} AND
                    u.is_bot = 0
                ORDER BY
                    e.experience_points DESC
                LIMIT
                    %s;
                """

        self.cursor.execute(query, (amount,))
        experiences_db = self.cursor.fetchall()
        response = "Experiências: \n\n"
        for experience in experiences_db:
            first_name = experience[0]
            last_name = experience[1]
            username = experience[2]
            experience = experience[3]
            response += f"""{first_name} {last_name} ({experience})\n"""
        return response
