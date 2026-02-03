"""Text processing utilities for emoji conversion and attachment handling."""

import re
from dataclasses import dataclass
from typing import Optional

# Emoji to shortcode mapping (common emojis)
# This uses standard shortcode names compatible with Discord/Slack
EMOJI_TO_SHORTCODE: dict[str, str] = {
    # Smileys & Emotion
    "😀": ":grinning:",
    "😃": ":smiley:",
    "😄": ":smile:",
    "😁": ":grin:",
    "😅": ":sweat_smile:",
    "😂": ":joy:",
    "🤣": ":rofl:",
    "😊": ":blush:",
    "😇": ":innocent:",
    "🙂": ":slight_smile:",
    "🙃": ":upside_down:",
    "😉": ":wink:",
    "😌": ":relieved:",
    "😍": ":heart_eyes:",
    "🥰": ":smiling_face_with_hearts:",
    "😘": ":kissing_heart:",
    "😗": ":kissing:",
    "😙": ":kissing_smiling_eyes:",
    "😚": ":kissing_closed_eyes:",
    "😋": ":yum:",
    "😛": ":stuck_out_tongue:",
    "😜": ":stuck_out_tongue_winking_eye:",
    "🤪": ":zany_face:",
    "😝": ":stuck_out_tongue_closed_eyes:",
    "🤑": ":money_mouth:",
    "🤗": ":hugs:",
    "🤭": ":hand_over_mouth:",
    "🤫": ":shushing_face:",
    "🤔": ":thinking:",
    "🤐": ":zipper_mouth:",
    "🤨": ":raised_eyebrow:",
    "😐": ":neutral_face:",
    "😑": ":expressionless:",
    "😶": ":no_mouth:",
    "😏": ":smirk:",
    "😒": ":unamused:",
    "🙄": ":rolling_eyes:",
    "😬": ":grimacing:",
    "😮‍💨": ":exhaling:",
    "🤥": ":lying_face:",
    "😌": ":relieved:",
    "😔": ":pensive:",
    "😪": ":sleepy:",
    "🤤": ":drooling_face:",
    "😴": ":sleeping:",
    "😷": ":mask:",
    "🤒": ":thermometer_face:",
    "🤕": ":head_bandage:",
    "🤢": ":nauseated_face:",
    "🤮": ":vomiting:",
    "🤧": ":sneezing_face:",
    "🥵": ":hot_face:",
    "🥶": ":cold_face:",
    "🥴": ":woozy_face:",
    "😵": ":dizzy_face:",
    "🤯": ":exploding_head:",
    "🤠": ":cowboy:",
    "🥳": ":partying_face:",
    "🥸": ":disguised_face:",
    "😎": ":sunglasses:",
    "🤓": ":nerd:",
    "🧐": ":monocle_face:",
    "😕": ":confused:",
    "😟": ":worried:",
    "🙁": ":slight_frown:",
    "☹️": ":frowning:",
    "😮": ":open_mouth:",
    "😯": ":hushed:",
    "😲": ":astonished:",
    "😳": ":flushed:",
    "🥺": ":pleading_face:",
    "😦": ":frowning_with_open_mouth:",
    "😧": ":anguished:",
    "😨": ":fearful:",
    "😰": ":cold_sweat:",
    "😥": ":disappointed_relieved:",
    "😢": ":cry:",
    "😭": ":sob:",
    "😱": ":scream:",
    "😖": ":confounded:",
    "😣": ":persevere:",
    "😞": ":disappointed:",
    "😓": ":sweat:",
    "😩": ":weary:",
    "😫": ":tired_face:",
    "🥱": ":yawning_face:",
    "😤": ":triumph:",
    "😡": ":rage:",
    "😠": ":angry:",
    "🤬": ":cursing_face:",
    "😈": ":smiling_imp:",
    "👿": ":imp:",
    "💀": ":skull:",
    "☠️": ":skull_crossbones:",
    "💩": ":poop:",
    "🤡": ":clown:",
    "👹": ":ogre:",
    "👺": ":goblin:",
    "👻": ":ghost:",
    "👽": ":alien:",
    "👾": ":space_invader:",
    "🤖": ":robot:",
    "😺": ":smiley_cat:",
    "😸": ":smile_cat:",
    "😹": ":joy_cat:",
    "😻": ":heart_eyes_cat:",
    "😼": ":smirk_cat:",
    "😽": ":kissing_cat:",
    "🙀": ":scream_cat:",
    "😿": ":crying_cat_face:",
    "😾": ":pouting_cat:",
    "🙈": ":see_no_evil:",
    "🙉": ":hear_no_evil:",
    "🙊": ":speak_no_evil:",
    "💋": ":kiss:",
    "💌": ":love_letter:",
    "💘": ":cupid:",
    "💝": ":gift_heart:",
    "💖": ":sparkling_heart:",
    "💗": ":heartpulse:",
    "💓": ":heartbeat:",
    "💞": ":revolving_hearts:",
    "💕": ":two_hearts:",
    "💟": ":heart_decoration:",
    "❣️": ":heart_exclamation:",
    "💔": ":broken_heart:",
    "❤️": ":heart:",
    "🧡": ":orange_heart:",
    "💛": ":yellow_heart:",
    "💚": ":green_heart:",
    "💙": ":blue_heart:",
    "💜": ":purple_heart:",
    "🤎": ":brown_heart:",
    "🖤": ":black_heart:",
    "🤍": ":white_heart:",
    "💯": ":100:",
    "💢": ":anger:",
    "💥": ":boom:",
    "💫": ":dizzy:",
    "💦": ":sweat_drops:",
    "💨": ":dash:",
    "🕳️": ":hole:",
    "💣": ":bomb:",
    "💬": ":speech_balloon:",
    "👁️‍🗨️": ":eye_speech_bubble:",
    "🗨️": ":left_speech_bubble:",
    "🗯️": ":right_anger_bubble:",
    "💭": ":thought_balloon:",
    "💤": ":zzz:",
    # Gestures & Body
    "👋": ":wave:",
    "🤚": ":raised_back_of_hand:",
    "🖐️": ":hand_splayed:",
    "✋": ":raised_hand:",
    "🖖": ":vulcan:",
    "👌": ":ok_hand:",
    "🤌": ":pinched_fingers:",
    "🤏": ":pinching_hand:",
    "✌️": ":v:",
    "🤞": ":crossed_fingers:",
    "🤟": ":love_you_gesture:",
    "🤘": ":metal:",
    "🤙": ":call_me:",
    "👈": ":point_left:",
    "👉": ":point_right:",
    "👆": ":point_up_2:",
    "🖕": ":middle_finger:",
    "👇": ":point_down:",
    "☝️": ":point_up:",
    "👍": ":thumbsup:",
    "👎": ":thumbsdown:",
    "✊": ":fist:",
    "👊": ":punch:",
    "🤛": ":left_fist:",
    "🤜": ":right_fist:",
    "👏": ":clap:",
    "🙌": ":raised_hands:",
    "👐": ":open_hands:",
    "🤲": ":palms_up:",
    "🤝": ":handshake:",
    "🙏": ":pray:",
    "✍️": ":writing_hand:",
    "💅": ":nail_care:",
    "🤳": ":selfie:",
    "💪": ":muscle:",
    "🦾": ":mechanical_arm:",
    "🦿": ":mechanical_leg:",
    "🦵": ":leg:",
    "🦶": ":foot:",
    "👂": ":ear:",
    "🦻": ":ear_with_hearing_aid:",
    "👃": ":nose:",
    "🧠": ":brain:",
    "👀": ":eyes:",
    "👁️": ":eye:",
    "👅": ":tongue:",
    "👄": ":lips:",
    # People & Family
    "👶": ":baby:",
    "🧒": ":child:",
    "👦": ":boy:",
    "👧": ":girl:",
    "🧑": ":person:",
    "👱": ":blond_person:",
    "👨": ":man:",
    "🧔": ":bearded_person:",
    "👩": ":woman:",
    "🧓": ":older_person:",
    "👴": ":older_man:",
    "👵": ":older_woman:",
    # Common objects & symbols
    "❤️‍🔥": ":heart_on_fire:",
    "❤️‍🩹": ":mending_heart:",
    "⭐": ":star:",
    "🌟": ":star2:",
    "✨": ":sparkles:",
    "⚡": ":zap:",
    "🔥": ":fire:",
    "💧": ":droplet:",
    "🌊": ":ocean:",
    "🎉": ":tada:",
    "🎊": ":confetti_ball:",
    "🎈": ":balloon:",
    "🎁": ":gift:",
    "🏆": ":trophy:",
    "🥇": ":first_place:",
    "🥈": ":second_place:",
    "🥉": ":third_place:",
    "⚽": ":soccer:",
    "🏀": ":basketball:",
    "🏈": ":football:",
    "⚾": ":baseball:",
    "🎮": ":video_game:",
    "🎲": ":game_die:",
    "🎯": ":dart:",
    "🎵": ":musical_note:",
    "🎶": ":notes:",
    "🎤": ":microphone:",
    "🎧": ":headphones:",
    "📱": ":iphone:",
    "💻": ":computer:",
    "⌨️": ":keyboard:",
    "🖥️": ":desktop:",
    "🖨️": ":printer:",
    "📷": ":camera:",
    "📹": ":video_camera:",
    "📺": ":tv:",
    "📻": ":radio:",
    "🔔": ":bell:",
    "🔕": ":no_bell:",
    "📢": ":loudspeaker:",
    "📣": ":mega:",
    "⏰": ":alarm_clock:",
    "⏱️": ":stopwatch:",
    "⏲️": ":timer:",
    "🕐": ":clock1:",
    "💡": ":bulb:",
    "🔦": ":flashlight:",
    "🔧": ":wrench:",
    "🔨": ":hammer:",
    "⚙️": ":gear:",
    "🔩": ":nut_and_bolt:",
    "🧲": ":magnet:",
    "💎": ":gem:",
    "💰": ":moneybag:",
    "💵": ":dollar:",
    "💴": ":yen:",
    "💶": ":euro:",
    "💷": ":pound:",
    "📧": ":email:",
    "📨": ":incoming_envelope:",
    "📩": ":envelope_with_arrow:",
    "📝": ":memo:",
    "📁": ":file_folder:",
    "📂": ":open_file_folder:",
    "📅": ":date:",
    "📆": ":calendar:",
    "📊": ":bar_chart:",
    "📈": ":chart_with_upwards_trend:",
    "📉": ":chart_with_downwards_trend:",
    "📌": ":pushpin:",
    "📍": ":round_pushpin:",
    "📎": ":paperclip:",
    "🔗": ":link:",
    "📏": ":straight_ruler:",
    "📐": ":triangular_ruler:",
    "✂️": ":scissors:",
    "🔒": ":lock:",
    "🔓": ":unlock:",
    "🔑": ":key:",
    "🔐": ":closed_lock_with_key:",
    # Food & Drink
    "🍕": ":pizza:",
    "🍔": ":hamburger:",
    "🍟": ":fries:",
    "🌭": ":hotdog:",
    "🍿": ":popcorn:",
    "🍩": ":doughnut:",
    "🍪": ":cookie:",
    "🎂": ":birthday:",
    "🍰": ":cake:",
    "🧁": ":cupcake:",
    "🍫": ":chocolate_bar:",
    "🍬": ":candy:",
    "🍭": ":lollipop:",
    "☕": ":coffee:",
    "🍵": ":tea:",
    "🧃": ":beverage_box:",
    "🍺": ":beer:",
    "🍻": ":beers:",
    "🥂": ":champagne_glass:",
    "🍷": ":wine_glass:",
    "🥃": ":tumbler_glass:",
    "🍸": ":cocktail:",
    "🍹": ":tropical_drink:",
    # Animals
    "🐶": ":dog:",
    "🐱": ":cat:",
    "🐭": ":mouse:",
    "🐹": ":hamster:",
    "🐰": ":rabbit:",
    "🦊": ":fox:",
    "🐻": ":bear:",
    "🐼": ":panda_face:",
    "🐨": ":koala:",
    "🐯": ":tiger:",
    "🦁": ":lion:",
    "🐮": ":cow:",
    "🐷": ":pig:",
    "🐸": ":frog:",
    "🐵": ":monkey_face:",
    "🐔": ":chicken:",
    "🐧": ":penguin:",
    "🐦": ":bird:",
    "🐤": ":baby_chick:",
    "🦆": ":duck:",
    "🦅": ":eagle:",
    "🦉": ":owl:",
    "🦇": ":bat:",
    "🐺": ":wolf:",
    "🐗": ":boar:",
    "🐴": ":horse:",
    "🦄": ":unicorn:",
    "🐝": ":bee:",
    "🐛": ":bug:",
    "🦋": ":butterfly:",
    "🐌": ":snail:",
    "🐞": ":ladybug:",
    "🐜": ":ant:",
    "🦟": ":mosquito:",
    "🦗": ":cricket:",
    "🕷️": ":spider:",
    "🦂": ":scorpion:",
    "🐢": ":turtle:",
    "🐍": ":snake:",
    "🦎": ":lizard:",
    "🐙": ":octopus:",
    "🦑": ":squid:",
    "🦐": ":shrimp:",
    "🦀": ":crab:",
    "🐡": ":blowfish:",
    "🐠": ":tropical_fish:",
    "🐟": ":fish:",
    "🐬": ":dolphin:",
    "🐳": ":whale:",
    "🐋": ":whale2:",
    "🦈": ":shark:",
    "🐊": ":crocodile:",
    "🐅": ":tiger2:",
    "🐆": ":leopard:",
    "🦓": ":zebra:",
    "🦍": ":gorilla:",
    "🦧": ":orangutan:",
    "🐘": ":elephant:",
    "🦛": ":hippo:",
    "🦏": ":rhino:",
    "🐪": ":camel:",
    "🐫": ":two_hump_camel:",
    "🦒": ":giraffe:",
    "🦘": ":kangaroo:",
    "🐃": ":water_buffalo:",
    "🐂": ":ox:",
    "🐄": ":cow2:",
    "🐎": ":racehorse:",
    "🐖": ":pig2:",
    "🐏": ":ram:",
    "🐑": ":sheep:",
    "🐐": ":goat:",
    "🦌": ":deer:",
    "🐕": ":dog2:",
    "🐩": ":poodle:",
    "🦮": ":guide_dog:",
    "🐕‍🦺": ":service_dog:",
    "🐈": ":cat2:",
    "🐈‍⬛": ":black_cat:",
    "🐓": ":rooster:",
    "🦃": ":turkey:",
    "🦚": ":peacock:",
    "🦜": ":parrot:",
    "🦢": ":swan:",
    "🦩": ":flamingo:",
    "🕊️": ":dove:",
    "🐇": ":rabbit2:",
    "🦝": ":raccoon:",
    "🦨": ":skunk:",
    "🦡": ":badger:",
    "🦫": ":beaver:",
    "🦦": ":otter:",
    "🦥": ":sloth:",
    "🐁": ":mouse2:",
    "🐀": ":rat:",
    "🐿️": ":chipmunk:",
    "🦔": ":hedgehog:",
    # Nature
    "🌸": ":cherry_blossom:",
    "💮": ":white_flower:",
    "🏵️": ":rosette:",
    "🌹": ":rose:",
    "🥀": ":wilted_flower:",
    "🌺": ":hibiscus:",
    "🌻": ":sunflower:",
    "🌼": ":blossom:",
    "🌷": ":tulip:",
    "🌱": ":seedling:",
    "🌲": ":evergreen_tree:",
    "🌳": ":deciduous_tree:",
    "🌴": ":palm_tree:",
    "🌵": ":cactus:",
    "🌾": ":ear_of_rice:",
    "🌿": ":herb:",
    "☘️": ":shamrock:",
    "🍀": ":four_leaf_clover:",
    "🍁": ":maple_leaf:",
    "🍂": ":fallen_leaf:",
    "🍃": ":leaves:",
    "🍄": ":mushroom:",
    "🌰": ":chestnut:",
    "🌍": ":earth_africa:",
    "🌎": ":earth_americas:",
    "🌏": ":earth_asia:",
    "🌑": ":new_moon:",
    "🌒": ":waxing_crescent_moon:",
    "🌓": ":first_quarter_moon:",
    "🌔": ":waxing_gibbous_moon:",
    "🌕": ":full_moon:",
    "🌖": ":waning_gibbous_moon:",
    "🌗": ":last_quarter_moon:",
    "🌘": ":waning_crescent_moon:",
    "🌙": ":crescent_moon:",
    "🌚": ":new_moon_with_face:",
    "🌛": ":first_quarter_moon_with_face:",
    "🌜": ":last_quarter_moon_with_face:",
    "🌝": ":full_moon_with_face:",
    "🌞": ":sun_with_face:",
    "☀️": ":sunny:",
    "⛅": ":partly_sunny:",
    "🌤️": ":sun_behind_small_cloud:",
    "🌥️": ":sun_behind_large_cloud:",
    "🌦️": ":sun_behind_rain_cloud:",
    "🌧️": ":cloud_rain:",
    "🌨️": ":cloud_snow:",
    "🌩️": ":cloud_lightning:",
    "🌪️": ":tornado:",
    "🌫️": ":fog:",
    "🌬️": ":wind_face:",
    "🌀": ":cyclone:",
    "🌈": ":rainbow:",
    "☁️": ":cloud:",
    "❄️": ":snowflake:",
    "☃️": ":snowman:",
    "⛄": ":snowman_without_snow:",
    "☄️": ":comet:",
    # Symbols
    "✅": ":white_check_mark:",
    "❌": ":x:",
    "❓": ":question:",
    "❔": ":grey_question:",
    "❕": ":grey_exclamation:",
    "❗": ":exclamation:",
    "‼️": ":bangbang:",
    "⁉️": ":interrobang:",
    "⚠️": ":warning:",
    "🚫": ":no_entry_sign:",
    "🔴": ":red_circle:",
    "🟠": ":orange_circle:",
    "🟡": ":yellow_circle:",
    "🟢": ":green_circle:",
    "🔵": ":blue_circle:",
    "🟣": ":purple_circle:",
    "🟤": ":brown_circle:",
    "⚫": ":black_circle:",
    "⚪": ":white_circle:",
    "🔺": ":small_red_triangle:",
    "🔻": ":small_red_triangle_down:",
    "🔶": ":large_orange_diamond:",
    "🔷": ":large_blue_diamond:",
    "🔸": ":small_orange_diamond:",
    "🔹": ":small_blue_diamond:",
    "▪️": ":black_small_square:",
    "▫️": ":white_small_square:",
    "◾": ":black_medium_small_square:",
    "◽": ":white_medium_small_square:",
    "◼️": ":black_medium_square:",
    "◻️": ":white_medium_square:",
    "⬛": ":black_large_square:",
    "⬜": ":white_large_square:",
    "🔲": ":black_square_button:",
    "🔳": ":white_square_button:",
    "➕": ":heavy_plus_sign:",
    "➖": ":heavy_minus_sign:",
    "➗": ":heavy_division_sign:",
    "✖️": ":heavy_multiplication_x:",
    "♾️": ":infinity:",
    "💲": ":heavy_dollar_sign:",
    "™️": ":tm:",
    "©️": ":copyright:",
    "®️": ":registered:",
    "〰️": ":wavy_dash:",
    "➰": ":curly_loop:",
    "➿": ":loop:",
    "🔚": ":end:",
    "🔙": ":back:",
    "🔛": ":on:",
    "🔜": ":soon:",
    "🔝": ":top:",
    "🆕": ":new:",
    "🆓": ":free:",
    "🆗": ":ok:",
    "🆒": ":cool:",
    "🆙": ":up:",
    "🆖": ":ng:",
    "ℹ️": ":information_source:",
    "🅰️": ":a:",
    "🅱️": ":b:",
    "🆎": ":ab:",
    "🅾️": ":o2:",
    "🔠": ":capital_abcd:",
    "🔡": ":abcd:",
    "🔢": ":1234:",
    "🔣": ":symbols:",
    "🔤": ":abc:",
    "#️⃣": ":hash:",
    "*️⃣": ":asterisk:",
    "0️⃣": ":zero:",
    "1️⃣": ":one:",
    "2️⃣": ":two:",
    "3️⃣": ":three:",
    "4️⃣": ":four:",
    "5️⃣": ":five:",
    "6️⃣": ":six:",
    "7️⃣": ":seven:",
    "8️⃣": ":eight:",
    "9️⃣": ":nine:",
    "🔟": ":keycap_ten:",
    "🔀": ":twisted_rightwards_arrows:",
    "🔁": ":repeat:",
    "🔂": ":repeat_one:",
    "▶️": ":arrow_forward:",
    "⏩": ":fast_forward:",
    "⏭️": ":track_next:",
    "⏯️": ":play_pause:",
    "◀️": ":arrow_backward:",
    "⏪": ":rewind:",
    "⏮️": ":track_previous:",
    "🔼": ":arrow_up_small:",
    "⏫": ":arrow_double_up:",
    "🔽": ":arrow_down_small:",
    "⏬": ":arrow_double_down:",
    "⏸️": ":pause_button:",
    "⏹️": ":stop_button:",
    "⏺️": ":record_button:",
    "⏏️": ":eject:",
    "🎦": ":cinema:",
    "🔅": ":low_brightness:",
    "🔆": ":high_brightness:",
    "📶": ":signal_strength:",
    "📳": ":vibration_mode:",
    "📴": ":mobile_phone_off:",
    "♻️": ":recycle:",
    "🔱": ":trident:",
    "📛": ":name_badge:",
    "🔰": ":beginner:",
    "⭕": ":o:",
    "✔️": ":heavy_check_mark:",
    "☑️": ":ballot_box_with_check:",
    "✳️": ":eight_spoked_asterisk:",
    "✴️": ":eight_pointed_black_star:",
    "❇️": ":sparkle:",
    "〽️": ":part_alternation_mark:",
    "🔘": ":radio_button:",
    "🏳️": ":white_flag:",
    "🏴": ":black_flag:",
    "🚩": ":triangular_flag_on_post:",
}

# Build reverse mapping (shortcode to emoji)
SHORTCODE_TO_EMOJI: dict[str, str] = {v: k for k, v in EMOJI_TO_SHORTCODE.items()}


# Content type to display name mapping
CONTENT_TYPE_NAMES: dict[str, str] = {
    # Images
    "image/jpeg": "Image",
    "image/jpg": "Image",
    "image/png": "Image",
    "image/gif": "GIF",
    "image/webp": "Image",
    "image/bmp": "Image",
    "image/svg+xml": "Image",
    # Audio
    "audio/aac": "Voice Note",
    "audio/mp4": "Voice Note",
    "audio/mpeg": "Audio",
    "audio/ogg": "Voice Note",
    "audio/wav": "Audio",
    "audio/webm": "Voice Note",
    "audio/x-m4a": "Audio",
    # Video
    "video/mp4": "Video",
    "video/webm": "Video",
    "video/quicktime": "Video",
    "video/3gpp": "Video",
    # Documents
    "application/pdf": "PDF",
    "application/msword": "Document",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "Document",
    "application/vnd.ms-excel": "Spreadsheet",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "Spreadsheet",
    "application/vnd.ms-powerpoint": "Presentation",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "Presentation",
    "application/zip": "Archive",
    "application/x-rar-compressed": "Archive",
    "application/x-7z-compressed": "Archive",
    "application/gzip": "Archive",
    "text/plain": "Text File",
    "text/csv": "CSV",
    "application/json": "JSON",
    "application/xml": "XML",
}


@dataclass
class Attachment:
    """Represents a Signal message attachment."""

    content_type: str
    filename: Optional[str] = None
    size: Optional[int] = None
    id: Optional[str] = None

    @property
    def display_type(self) -> str:
        """Get human-readable attachment type."""
        # Check content type mapping
        if self.content_type in CONTENT_TYPE_NAMES:
            return CONTENT_TYPE_NAMES[self.content_type]

        # Fallback to generic categories based on mime type prefix
        if self.content_type.startswith("image/"):
            return "Image"
        elif self.content_type.startswith("audio/"):
            return "Audio"
        elif self.content_type.startswith("video/"):
            return "Video"
        elif self.content_type.startswith("text/"):
            return "Text File"

        # Default
        return "File"


def emoji_to_shortcode(text: str) -> str:
    """Convert Unicode emojis to :shortcode: format.

    Args:
        text: Text potentially containing emojis

    Returns:
        Text with emojis converted to shortcodes
    """
    if not text:
        return text

    result = text
    for emoji, shortcode in EMOJI_TO_SHORTCODE.items():
        result = result.replace(emoji, shortcode)

    return result


def shortcode_to_emoji(text: str) -> str:
    """Convert :shortcode: format back to Unicode emojis.

    Args:
        text: Text potentially containing shortcodes

    Returns:
        Text with shortcodes converted to emojis
    """
    if not text:
        return text

    # Use regex to find all :shortcode: patterns
    def replace_shortcode(match: re.Match) -> str:
        shortcode = match.group(0)
        return SHORTCODE_TO_EMOJI.get(shortcode, shortcode)

    # Match :word: patterns (allowing underscores and numbers)
    pattern = r":[a-z0-9_]+:"
    return re.sub(pattern, replace_shortcode, text)


def format_attachment(attachment: Attachment) -> str:
    """Format a single attachment for display.

    Args:
        attachment: The attachment to format

    Returns:
        Formatted attachment string like [Image] or [File: document.pdf]
    """
    display_type = attachment.display_type

    # For generic files, include filename if available
    if display_type == "File" and attachment.filename:
        return f"[File: {attachment.filename}]"

    # For known types, just show the type
    # But include filename for documents if it's informative
    if display_type in ("PDF", "Document", "Spreadsheet", "Presentation", "Archive", "Text File", "CSV", "JSON", "XML"):
        if attachment.filename:
            return f"[{display_type}: {attachment.filename}]"

    return f"[{display_type}]"


def format_attachments(attachments: list[Attachment]) -> str:
    """Format multiple attachments for display.

    Args:
        attachments: List of attachments to format

    Returns:
        Formatted string representing all attachments
    """
    if not attachments:
        return ""

    return " ".join(format_attachment(a) for a in attachments)


def format_sticker() -> str:
    """Format a sticker for display.

    Returns:
        Formatted sticker string
    """
    return "[Sticker]"


def process_signal_to_game(text: str, attachments: Optional[list[Attachment]] = None, has_sticker: bool = False) -> str:
    """Process a Signal message for sending to the game.

    Converts emojis to shortcodes and appends attachment indicators.

    Args:
        text: The message text (may be empty)
        attachments: List of attachments (may be None or empty)
        has_sticker: Whether a sticker was included

    Returns:
        Processed text suitable for game chat
    """
    parts = []

    # Convert emojis in text
    if text:
        parts.append(emoji_to_shortcode(text))

    # Add sticker indicator
    if has_sticker:
        parts.append(format_sticker())

    # Add attachment indicators
    if attachments:
        parts.append(format_attachments(attachments))

    return " ".join(parts) if parts else ""


def process_game_to_signal(text: str) -> str:
    """Process a game message for sending to Signal.

    Converts shortcodes back to emojis.

    Args:
        text: The message text from the game

    Returns:
        Processed text with emojis restored
    """
    if not text:
        return text

    return shortcode_to_emoji(text)


def parse_attachments(raw_attachments: list[dict]) -> list[Attachment]:
    """Parse raw attachment data from Signal API.

    Args:
        raw_attachments: List of attachment dictionaries from Signal API

    Returns:
        List of Attachment objects
    """
    attachments = []
    for raw in raw_attachments:
        attachments.append(Attachment(
            content_type=raw.get("contentType", "application/octet-stream"),
            filename=raw.get("filename"),
            size=raw.get("size"),
            id=raw.get("id"),
        ))
    return attachments
