from classQuery import *
import pdb

class Souvenirs(object):

    format_index_pref = ':%(lengthL)i:%(lengthR)i:%(side)i:%(op)i:'
    format_index_suff = '%(buk)i:%(col)i:'
    def __init__(self,  nAvailableMo, nAmnesic = False):
        self.queriesList = []
        self.indexes = {}
        self.availableMo = [set(nAvailableMo[0]), set(nAvailableMo[1])]
        self.amnesic = nAmnesic

    def cutOffSide(self, side):
        self.availableMo[side] = set()

    def nbCols(self, side):
        return len(self.availableMo[side])

    def isAmnesic(self):
        return self.amnesic
    
    def __str__(self):
        if self.isAmnesic():
            return 'Amnesic, Availables :%i x %i' % (len(self.availableMo[0]), len(self.availableMo[1]))
        else :
            return '%i souvenirs, %i indexes, Availables :%i x %i' \
                   % (len(self.queriesList), len(self.indexes), len(self.availableMo[0]), len(self.availableMo[1]))
    
    def count(self):
        return len(self.queriesList)
    
    def nextId(self):
        return len(self.queriesList)
        
    def add(self, red):
        if len(red) > 2:
        # TODO CHECK: if ( red.nbAvailableCols() > 0 and len(red) > 2 ) or (red.fullLength(0) and red.fullLength(1)):
            #print 'ADDED SOUVENIR----' + red.queries[0].dispIds() + '<=>' + red.queries[1].dispIds()
    
            ix = self.nextId()
            for indx in self.makeOwnIndexes(red):
                if indx in self.indexes:
                    self.indexes[indx].add(ix)
                else:
                    self.indexes[indx] = set([ix])
            self.queriesList.append((red.queries[0], red.queries[1], red.score()))
        
    def makeIndexes(self, red, lengthL, lengthR, side, op):
        return red.queries[side].makeIndexes((self.format_index_pref % {'lengthL': lengthL, 'lengthR': lengthR, 'side': side, 'op': op}) + self.format_index_suff)
                        
    def makeOwnIndexes(self, red):
        indexes = []
        for side in [0,1]:
            indexes.extend(self.makeIndexes(red, red.length(0), red.length(1), side, red.queries[side].opBuk(0)))
        return indexes
    
    def extOneStep(self, red, side):
        cols_ext = red.invColsSide(side)
        if not self.isAmnesic():
            other_side = 1-side
            lengthL = red.length(0)+(1-side)
            lengthR = red.length(1)+side

            queries_ids_other_side = self.lookForQueries(self.makeIndexes(red, lengthL, lengthR, other_side, red.queries[other_side].opBuk(0)))
            if len(queries_ids_other_side ) > 0:
#                pdb.set_trace()
                if red.length(side) == 1:
                    queries_ids = self.lookForQueries(self.makeIndexes(red, lengthL, lengthR, side, Op(True))) 
                    queries_ids |= self.lookForQueries(self.makeIndexes(red, lengthL, lengthR, side, Op(False)))
                else:
                    queries_ids = self.lookForQueries(self.makeIndexes(red, lengthL, lengthR, side, red.queries[side].opBuk(0)))

                queries_ids &= queries_ids_other_side
                if len(queries_ids) > 0:
                    
                    # print 'EXTENSIONS-%i------%s <=> %s -------' % (side, red.queries[0].dispIds(),red.queries[1].dispIds())
#                     for i in queries_ids:
#                         print self.queriesList[i][0].dispIds() + '<=>' + self.queriesList[i][1].dispIds() 
#                     print '------------------------'
                    cols_ext = self.colsExtending(queries_ids, side) ## includes already used cols
#             if len(cols_ext) > red.queries[side].length() :
#                 print 'EXCLUDED-%i-------------' % side
#                 print cols_ext
#                 print '------------------------'
        
        return cols_ext   
                
#     def extOneStepFromInitial(self, initialPair, side):
#         cols_ext = set([initialPair[side+1]])
#         nb_cols_own = 1
#         if not self.amnesic:
#             other_side = 1-side
#             lengthL = 1+(1-side)
#             lengthR = 1+side
#             col_side = query_colX(initialPair[side+1], initialPair[side+3])
#             col_other = query_colX(initialPair[other_side+1], initialPair[other_side+3])

#             indexes_other_side = [(self.format_index_pref + self.format_index_suff) % {'lengthL': lengthL, 'lengthR': lengthR, 'side': other_side, 'op': -1, 'col': col_other, 'buk': 1} ]
#             indexes_OR = [(self.format_index_pref + self.format_index_suff) % {'lengthL': lengthL, 'lengthR': lengthR, 'side': side, 'op': 1, 'col': col_side, 'buk': 1} ]
#             indexes_AND = [(self.format_index_pref + self.format_index_suff) % {'lengthL': lengthL, 'lengthR': lengthR, 'side': side, 'op': 0, 'col': col_side, 'buk': 1} ]

#             queries_ids_other_side = self.lookForQueries(indexes_other_side)
#             if len(queries_ids_other_side ) > 0:
#                 #pdb.set_trace()
#                 queries_ids = self.lookForQueries(indexes_OR)
#                 queries_ids |= self.lookForQueries(indexes_AND)
#                 queries_ids &= queries_ids_other_side
#                 if len(queries_ids) > 0:
                    
#                    #  print 'EXTENSIONS-%i-----%s--------' % (side, initialPair)
# #                     for i in queries_ids:
# #                         print self.queriesList[i][0].dispIds() + '<=>' + self.queriesList[i][1].dispIds()
# #                     print '------------------------'
                    
#                     cols_ext = self.colsExtending(queries_ids, side) ## includes already used cols
#             # if len(cols_ext) > 1 :
# #                 print 'EXCLUDED-%i-------------' % side
# #                 print cols_ext
# #             print '------------------------'
#         return cols_ext
    
    def initialAvailable(self, initialPairRed):
        return [self.availableMo[0] - self.extOneStep(initialPairRed, 0), \
                self.availableMo[1] - self.extOneStep(initialPairRed, 1)]

        
    def colsExtending(self, queries_ids, side):
        cols = set()
        for idr in queries_ids:
            cols |= self.queriesList[idr][side].invCols()
        return cols  

    def lookForQueries(self, indexes_p):
        if len(indexes_p) > 0 and not self.isAmnesic():
            query_ids = set([-1])
            id_inds = 0
            while id_inds < len(indexes_p) and indexes_p[id_inds] in self.indexes and len(query_ids) > 0:
                if id_inds ==0 :
                    query_ids = set(self.indexes[indexes_p[id_inds]])
                else:
                    query_ids &= self.indexes[indexes_p[id_inds]]
                id_inds +=1
            if id_inds != len(indexes_p):
                query_ids = set()
            return query_ids
        else:
            return set()
        
    def update(self, redList):
        for red in redList:
            if not self.isAmnesic():
                self.add(red)

        
