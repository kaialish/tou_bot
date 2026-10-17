# -*- coding: utf-8 -*-
from src.services.parser import parse_zhurnal, format_zhurnal_brief, format_zhurnal_full_chunks

sample_html = '''
<div>Неделя: <b>7</b>, Числитель</div>
<section class="student-card student-zhurnal__course"><div class="student-zhurnal__course-head"><h2>История Казахстана (ГЭ)</h2><div class="student-zhurnal__teachers"><span class="student-zhurnal__teacher"><span class="student-zhurnal__teacher-types">Лекции</span><span class="student-zhurnal__teacher-fio">Шабамбаева Анара Габдулбариевна</span></span><span class="student-zhurnal__teacher"><span class="student-zhurnal__teacher-types">Практические/Семинарские</span><span class="student-zhurnal__teacher-fio">Кулумбаева Майса Жумабаевна</span></span></div></div><div class="student-zhurnal__scroll"><table class="table1"><tbody><tr><td rowspan="3">Входной контроль</td><td colspan="23">1 рейтинг</td><td colspan="21">2 рейтинг</td><td rowspan="3">Рейтинг допуска</td><td rowspan="3">Экзамен/ Зачет</td><td rowspan="2" colspan="2">Курсовая работа/ Курсовой проект</td><td rowspan="3">Итоговая оценка</td></tr><tr><td colspan="9">Лекции</td><td colspan="9">Практические/Семинарские</td><td colspan="2">Текущие</td><td colspan="2">Из ведомости</td><td rowspan="2">Р1</td><td colspan="8">Лекции</td><td colspan="8">Практические/Семинарские</td><td colspan="2">Текущие</td><td colspan="2">Из ведомости</td><td rowspan="2">Р2</td></tr><tr><td>1</td><td>2</td><td>3</td><td>4</td><td>5</td><td>6</td><td>7</td><td>8</td><td>Сред. знач.</td><td>1</td><td>2</td><td>3</td><td>4</td><td>5</td><td>6</td><td>7</td><td>8</td><td>Сред. знач.</td><td>ТУ1</td><td>РК1</td><td>ТУ1</td><td>РК1</td><td>9</td><td>10</td><td>11</td><td>12</td><td>13</td><td>14</td><td>15</td><td>Сред. знач.</td><td>9</td><td>10</td><td>11</td><td>12</td><td>13</td><td>14</td><td>15</td><td>Сред. знач.</td><td>ТУ2</td><td>РК2</td><td>ТУ2</td><td>РК2</td><td>Из ведомости</td><td>из журнала</td></tr><tr><td>не выставлен</td><td>80</td><td>80</td><td>80</td><td>80</td><td>80</td><td>80</td><td>0</td><td>0</td><td>60.00</td><td>70</td><td>60</td><td>50</td><td>65</td><td>0</td><td>0</td><td>0</td><td>0</td><td>30.63</td><td>45.32</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0.00</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0.00</td><td>0.00</td><td></td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td> нет </td><td></td><td>0</td></tr></tbody></table></div></section>
'''

res = parse_zhurnal(sample_html)
print('Current week found:', res['current_week'])
b = format_zhurnal_brief(res)
f = format_zhurnal_full_chunks(res)

with open('scratch/week7_brief.txt', 'w', encoding='utf-8') as file:
    file.write(b)
with open('scratch/week7_full.txt', 'w', encoding='utf-8') as file:
    file.write(f[0])

print('Successfully written!')
