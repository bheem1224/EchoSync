var e = 1024, t = 2048, n = 4096, r = 8192, i = 32768, a = 1 << 25, o = 65536, s = 1 << 19, c = 1 << 20, l = 1 << 25, u = 1 << 21, d = 1 << 22, f = 1 << 23, p = 1 << 27, m = 1 << 26, h = Symbol("$state"), g = Symbol("component"), ee = Symbol("legacy props"), te = Symbol(""), ne = Symbol("attributes"), _ = Symbol("class"), v = Symbol("style"), re = Symbol("text"), ie = Symbol("form reset"), ae = new class extends Error {
	name = "StaleReactionError";
	message = "The reaction that called `getAbortSignal()` was re-run or destroyed";
}(), oe = !!globalThis.document?.contentType && /* @__PURE__ */ globalThis.document.contentType.includes("xml"), y = {}, b = Symbol("uninitialized");
function se() {
	console.warn("https://svelte.dev/e/derived_inert");
}
function ce(e) {
	console.warn("https://svelte.dev/e/hydration_mismatch");
}
function le() {
	console.warn("https://svelte.dev/e/svelte_boundary_reset_noop");
}
// node_modules/svelte/src/internal/client/dom/hydration.js
var x = !1;
function ue(e) {
	x = e;
}
var S;
function C(e) {
	if (e === null) throw ce(), y;
	return S = e;
}
function de() {
	return C(/* @__PURE__ */ Mr(S));
}
function w(e) {
	if (x) {
		if (/* @__PURE__ */ Mr(S) !== null) throw ce(), y;
		S = e;
	}
}
function fe(e = 1) {
	if (x) {
		for (var t = e, n = S; t--;) n = /* @__PURE__ */ Mr(n);
		S = n;
	}
}
function pe(e = !0) {
	for (var t = 0, n = S;;) {
		if (Br(n) === 8) {
			var r = Zr(n) ?? "";
			if (r === "]") {
				if (t === 0) return n;
				--t;
			} else (r === "[" || r === "[!" || r.startsWith("[?") || r[0] === "[" && !isNaN(Number(r.slice(1)))) && (t += 1);
		}
		var i = /* @__PURE__ */ Mr(n);
		e && qr(n), n = i;
	}
}
function me(e) {
	if (!e || Br(e) !== 8) throw ce(), y;
	return Zr(e) ?? "";
}
// node_modules/svelte/src/internal/shared/utils.js
var he = Array.isArray, ge = Array.prototype.indexOf, _e = Array.prototype.includes, ve = Array.from, ye = Object.keys, be = Object.defineProperty, xe = Object.getOwnPropertyDescriptor, Se = Object.getOwnPropertyDescriptors, Ce = Object.prototype, we = Array.prototype, Te = Object.getPrototypeOf, Ee = Object.isExtensible, De = () => {};
function Oe(e) {
	return e();
}
function ke(e) {
	for (var t = 0; t < e.length; t++) e[t]();
}
function Ae() {
	var e, t;
	return {
		promise: new Promise((n, r) => {
			e = n, t = r;
		}),
		resolve: e,
		reject: t
	};
}
function je(e) {
	var t = W;
	if (t === null) return e;
	if (!(t.f & 32768) && !(t.f & 4)) throw e;
	Me(e, t);
}
function Me(e, t) {
	if (e === y) throw e;
	if (!(t !== null && t.f & 16384)) {
		for (; t !== null;) {
			if (t.f & 128 && !(t.f & 33570816)) {
				if (!(t.f & 32768)) throw e;
				try {
					t.b.error(e);
					return;
				} catch (t) {
					e = t;
				}
			}
			t = t.parent;
		}
		throw e;
	}
}
function Ne(e) {
	throw Error("https://svelte.dev/e/lifecycle_outside_component");
}
function Pe(e) {
	throw Error("https://svelte.dev/e/effect_in_teardown");
}
function Fe() {
	throw Error("https://svelte.dev/e/effect_in_unowned_derived");
}
function Ie(e) {
	throw Error("https://svelte.dev/e/effect_orphan");
}
function Le() {
	throw Error("https://svelte.dev/e/effect_update_depth_exceeded");
}
function Re() {
	throw Error("https://svelte.dev/e/hydration_failed");
}
function ze(e) {
	throw Error("https://svelte.dev/e/props_invalid_value");
}
function Be() {
	throw Error("https://svelte.dev/e/state_descriptors_fixed");
}
function Ve() {
	throw Error("https://svelte.dev/e/state_prototype_fixed");
}
function He() {
	throw Error("https://svelte.dev/e/state_unsafe_mutation");
}
function Ue() {
	throw Error("https://svelte.dev/e/svelte_boundary_reset_onerror");
}
// node_modules/svelte/src/internal/flags/index.js
var We = !1;
function Ge() {
	We = !0;
}
// node_modules/svelte/src/internal/client/context.js
var T = null;
function Ke(e) {
	T = e;
}
function qe(e, t = !1, n) {
	T = {
		p: T,
		i: !1,
		c: null,
		e: null,
		s: e,
		x: null,
		r: W,
		l: We && !t ? {
			s: null,
			u: null,
			$: []
		} : null
	};
}
function Je(e) {
	var t = T, n = t.e;
	if (n !== null) {
		t.e = null;
		for (var r of n) cn(r);
	}
	return e !== void 0 && (t.x = e), t.i = !0, T = t.p, Ye(e);
}
function Ye(e = {}) {
	return be(e, g, { value: !0 }), e;
}
function Xe() {
	return !We || T !== null && T.l === null;
}
// node_modules/svelte/src/internal/client/dom/task.js
var Ze = [];
function Qe() {
	var e = Ze;
	Ze = [], ke(e);
}
function E(e) {
	if (Ze.length === 0 && !Lt) {
		var t = Ze;
		queueMicrotask(() => {
			t === Ze && Qe();
		});
	}
	Ze.push(e);
}
function $e() {
	for (; Ze.length > 0;) Qe();
}
// node_modules/svelte/src/internal/client/reactivity/equality.js
function et(e) {
	return e === this.v;
}
function tt(e, t) {
	return e == e ? e !== t || typeof e == "object" && !!e || typeof e == "function" : t == t;
}
function nt(e) {
	return !tt(e, this.v);
}
// node_modules/svelte/src/internal/client/custom-renderer/state.js
var rt = null;
// node_modules/svelte/src/internal/client/reactivity/async.js
function it(e, t, n, r) {
	var i = W, a = t.map(Xe() ? dt : ht), s = e.filter((e) => !e.settled);
	if (s.length > 0) {
		var c = at(), l = ct();
		(s.length === 1 ? s[0].promise : Promise.all(s.map((e) => e.promise))).then(() => {
			if (!(i.f & 16384)) {
				c(s[0].run.get_batch());
				try {
					u();
				} catch (e) {
					Me(e, i);
				}
				ot();
			}
		}).finally(l);
	} else u();
	function u() {
		if (!e.some((e) => e.failed)) {
			if (n.length === 0) r(a);
			else {
				var t = n.map((e) => /* @__PURE__ */ pt(e)), s = null;
				gn(() => {
					for (var e of t) if (mt(e)) {
						Z(e);
						return;
					}
					s === null ? s = R(() => {
						try {
							r([...a, ...t]);
						} catch (e) {
							Me(e, i);
						}
					}) : M.revalidate_branch(s);
				}, o);
			}
		}
	}
}
function at() {
	var e = W, t = V, n = T, r = M;
	return function(i = r) {
		G(e), U(t), Ke(n), i !== null && !(e.f & 16384) && D(i).activate();
	};
}
function ot(e = !0) {
	G(null), U(null), Ke(null), e && M?.deactivate();
}
var st = null;
function ct() {
	for (var e = W, t = e.b, n = D(M), r = t; r && !r.is_pending;) r = r.parent;
	return n.increment(e), r?.increment(e, n), t?.update_effect_pending(1), () => {
		D(n).decrement(e), r?.decrement(e, n), t?.update_effect_pending(-1);
	};
}
function D(e) {
	for (; e.merged !== null;) e = e.merged;
	return e;
}
// node_modules/svelte/src/internal/client/reactivity/status.js
var lt = ~(t | n | e);
function O(e, t) {
	e.f = e.f & lt | t;
}
function ut(t) {
	t.f & 512 || t.edges === null ? O(t, e) : O(t, n);
}
/*#__NO_SIDE_EFFECTS__*/
function dt(e) {
	var n = 2 | t;
	return W !== null && (W.f |= s), {
		ctx: T,
		deps: null,
		dv: null,
		edges: null,
		effects: null,
		equals: et,
		f: n,
		fn: e,
		reactions: null,
		rv: 0,
		v: b,
		wv: 0,
		parent: W,
		ac: null
	};
}
var ft = Symbol("obsolete");
/*#__NO_SIDE_EFFECTS__*/
function pt(e, t, n, r) {
	var i = wt(b);
	i.f |= d;
	var a = /* @__PURE__ */ new Set(), o = st, s = o && M, c = o && [];
	function l(e = !1) {
		var t = c;
		c = e ? null : [], e && (s = null);
		for (let e of t) e();
	}
	return pn(() => {
		var t = W, n = Ae();
		try {
			var u = e();
			if (u === b) return;
			var d = Promise.resolve(u), f = X?.signal;
			d.then((e) => {
				f?.aborted || n.resolve(e);
			}, (e) => {
				f?.aborted || e === ae && o === null || n.reject(e === ae ? ft : e);
			}).finally(ot);
		} catch (e) {
			n.reject(e);
		}
		var p = M, m = ct();
		p.async_deriveds.get(t)?.reject(ft), a.add(n), p.async_deriveds.set(t, n);
		let h = (e, u = void 0) => {
			if (c !== null && u !== ft && (s ??= p, D(p) !== D(s))) c.push(() => {
				var r = !!(t.f & 16384) || (p.linked ? p.async_deriveds.get(t) !== n : !D(p).linked);
				h(e, r ? ft : u);
			});
			else {
				if (m(), a.delete(n), u) {
					if (c !== null && s !== null && (a.size > 0 || u === ft) && D(s) === D(p) && D(p).async_deriveds.get(t) === n) {
						s = null, l();
						return;
					}
					if (u === ft) return;
				}
				var d = i.equals(e) && !u && !(i.f & 8388608);
				D(p).capture(i, u ?? e, d, !!u), o !== null && (o.switch(p), o.continued.push(() => l(!0)), o = null), r?.(u), r = void 0;
			}
		};
		n.promise.then(h, (e) => h(null, e || "unknown"));
	}), on(() => {
		for (let e of a) e.reject(ft);
	}), i;
}
function mt(e) {
	return (P?.get(e) ?? e).v === b;
}
/*#__NO_SIDE_EFFECTS__*/
function ht(e) {
	let t = /* @__PURE__ */ dt(e);
	return t.equals = nt, t;
}
function gt(e) {
	var t = e.effects;
	if (t !== null) {
		e.effects = null;
		for (var n = 0; n < t.length; n += 1) z(t[n]);
	}
}
function _t(e) {
	var t = W, n = e.parent;
	if (!B && n !== null && e.v !== b && n.f & 24576) return se(), ut(e), e.v;
	G(n);
	try {
		return gt(e), nr(e);
	} finally {
		G(t);
	}
}
function vt(e) {
	var t = e;
	if (Kn(t)) {
		var n = I?.records, r = n?.get(t);
		r !== void 0 && Un(r.deps, r.dv) ? (n.delete(t), lr(t, r)) : _t(t);
	}
}
function yt(e) {
	var t = F, n = t.get(e);
	if (n !== void 0) return n;
	var r = I, i = P.get(e), a = i ?? e, o = i === void 0 ? (e.f & m) !== 0 : i.assigned, s = r.get_record(e);
	return o && !Wn((s ?? e).deps, a.wv) ? n = a : s !== void 0 && Un(s.deps, s.dv) ? n = s : i === void 0 && !o && e.dv !== null && Un(e.deps, e.dv) ? n = e : (_t(e), n = r.records?.get(e) ?? e), e.f & 512 && t.set(e, n), n;
}
function bt(e) {
	if (e.effects !== null) for (let t of e.effects) (t.teardown || t.f & 134217728) && (t.teardown?.(), er(t), t.fn !== null && (t.teardown = De), mr(t), vn(t));
}
function xt(e) {
	if (e.effects !== null) for (let t of e.effects) t.teardown && t.fn !== null && hr(t);
}
// node_modules/svelte/src/internal/client/reactivity/sources.js
var St = /* @__PURE__ */ new Set(), Ct = !1;
function wt(e, t) {
	return {
		f: 0,
		v: e,
		reactions: null,
		equals: et,
		rv: 0,
		wv: 0
	};
}
/*#__NO_SIDE_EFFECTS__*/
function Tt(e, t) {
	let n = wt(e, t);
	return Fn(n), n;
}
/*#__NO_SIDE_EFFECTS__*/
function k(e, t = !1, n = !0) {
	let r = wt(e);
	return t || (r.equals = nt), We && n && T !== null && T.l !== null && (T.l.s ??= []).push(r), r;
}
function A(e, t, n = !1) {
	return V !== null && (!H || V.f & 131072) && Xe() && V.f & 4325394 && (K === null || !K.has(e)) && He(), Et(e, n ? wr(t) : t, zt);
}
function Et(e, t, n = null) {
	var r = e.equals(t) && !(e.f & 8388608), i = P?.get(e);
	if (!r || i !== void 0 && (i.e || !e.equals.call(i, t))) {
		var a = Gt.ensure();
		(e.f & 67110914) == 2050 && _t(e), a.capture(e, t, r, !1, n), Xe() && W !== null && W.f & 1024 && !(W.f & 96) && (Y === null ? In([e]) : Y.push(e));
	} else B && Pt(e);
	return t;
}
function Dt() {
	Ct = !1, en(Ot);
}
function Ot() {
	for (let e of St) {
		e.f & 1024 && O(e, n);
		let t;
		try {
			t = Kn(e);
		} catch {
			t = !0;
		}
		t && hr(e);
	}
	St.clear();
}
function kt(e) {
	A(e, e.v + 1);
}
// node_modules/svelte/src/internal/client/reactivity/batch.js
var j = null, At = null, M = null, jt = null, N = null;
function Mt(e) {
	N = e;
}
function Nt(e) {
	var t = N = {
		reverted_values: new Map(N?.reverted_values),
		derived_cache: /* @__PURE__ */ new Map(),
		parent: N
	};
	for (let [n, r] of e ?? []) t.reverted_values.set(n, r);
	return t;
}
function Pt(e) {
	for (var t = N; t !== null; t = t.parent) t.reverted_values.delete(e), t.derived_cache.clear();
}
var P = null, F = null, I = null, Ft = null, It = /* @__PURE__ */ new Set(), Lt = !1, Rt = null, zt = null, Bt = 0, Vt = null, Ht = 0, Ut = 1, Wt = null, Gt = class r {
	id = Ut++;
	started = !1;
	linked = !0;
	prev = null;
	next = null;
	async_deriveds = /* @__PURE__ */ new Map();
	current = /* @__PURE__ */ new Map();
	previous = /* @__PURE__ */ new Map();
	records = null;
	folded = [];
	#e = /* @__PURE__ */ new Map();
	#t = /* @__PURE__ */ new Map();
	#n = /* @__PURE__ */ new Map();
	#r = null;
	#i = /* @__PURE__ */ new Map();
	#a = [];
	#o = /* @__PURE__ */ new Set();
	#s = /* @__PURE__ */ new Set();
	is_fork = !1;
	merged = null;
	merge_requests = /* @__PURE__ */ new Set();
	#c = !1;
	constructor() {
		At === null ? j = At = this : (At.next = this, this.prev = At), At = this;
	}
	#l() {
		if (this.is_fork) return !0;
		for (let e of this.#n.keys()) if (this.is_blocked_by(e)) return !0;
		return !1;
	}
	#u(e) {
		return this.#o.has(e) || !!(e.f & 33554432) && !this.#s.has(e);
	}
	is_skipped(e) {
		for (var t = e; t !== null; t = t.parent) if (this.#u(t)) return !0;
		return !1;
	}
	is_blocked_by(e, t = null) {
		for (var n = e; n !== null && n !== t; n = n.parent) if (this.#u(n) || (n.f & 16512) == 128 && n.b.is_pending) return !1;
		return !0;
	}
	skip_effect(e) {
		this.#o.add(e), this.#s.delete(e);
	}
	unskip_effect(e) {
		(this.#o.delete(e) || !this.#s.has(e) && (e.f & 33554432 || this.folded.some((t) => t.#o.has(e)))) && this.revalidate_branch(e), this.#s.add(e);
	}
	unskip_new_effect(e) {
		this.#s.add(e);
	}
	revalidate_branch(e) {
		for (var t = e.first; t !== null; t = t.next) {
			var r = t.f;
			!(r & 24576) && !this.#u(t) && (!(r & 131168) && t.fn !== null && this.schedule(t, n), this.revalidate_branch(t));
		}
	}
	#d() {
		var t = [];
		for (let a of this.#a) if (!(a.f & 16384 || !(a.f & 6144))) {
			for (var n = a, r = !1; n.parent !== null;) {
				n = n.parent;
				var i = n.f;
				if (i & 96) {
					if (!(i & 1024)) {
						r = !0;
						break;
					}
					n.f ^= e;
				}
			}
			r || t.push(n);
		}
		return this.#a = [], t;
	}
	#f() {
		if (M = jt = this, N?.derived_cache.clear(), this.started = !0, Wt = this.id, this.#i.size > 0) {
			for (let [e, t] of this.#i) this.#S(e, t);
			this.#i.clear();
		}
		this.activate();
		for (var e = Rt = [], t = [], i = [], a = zt = []; this.#a.length > 0;) {
			Bt++ > 1e3 && (this.#T(), qt());
			for (let n of this.#d()) try {
				this.#m(n, e, t, i);
			} catch (e) {
				throw tn(n, !0), this.#l() || this.discard(), e;
			}
			if (this.#a.length > 0) {
				for (let e of t) this.#a.push(e);
				for (let t of e) this.#a.push(t);
				t.length = 0, e.length = 0;
			}
		}
		if (M = null, a.length > 0) {
			var o = r.ensure();
			for (let e of a) e.f & 1024 || o.schedule(e, n);
		}
		if (Rt = null, zt = null, this.merge_requests.size > 0) {
			let n = Array.from(this.merge_requests, D).filter((e) => e !== this && e.linked && !e.is_fork).sort((e, t) => e.id - t.id);
			if (this.merge_requests.clear(), n.length > 0) {
				this.#y(t), this.#y(e);
				for (var s = this, c = n.length; c--;) {
					var l = n[c];
					l !== s && (l.#_(s), s = l);
				}
				s.#f();
				return;
			}
		}
		if (this.#l()) {
			this.#y(t), this.#y(e);
			for (let e of this.#o) tn(e);
			a.length > 0 && M.#f();
			return;
		}
		let u = this.#h();
		if (u) this.#y(t), this.#y(e), u.#_(this), u.#f();
		else {
			for (let t of i) t.is_pending && t.is_ready(this) && t.reveal(e);
			this.#C(!0), this.#x(this.#e), Zt(e, Zt(t)), this.#r?.resolve();
			var d = M;
			if (this.#n.size === 0 && (this.#a.length === 0 || d !== null) && this.#T(), d !== null) {
				if (N !== null) for (let [e, t] of N.reverted_values) d.previous.get(e)?.wv !== t.wv && N.reverted_values.delete(e);
				d.#f();
			}
		}
	}
	#p(e) {
		var t = new Set(e), r = /* @__PURE__ */ new Set();
		for (let e of t) {
			var i = e.reactions;
			if (i !== null) for (let e of i) {
				var a = e.f;
				if (a & 2) a & 1024 && O(e, n), t.add(e);
				else {
					var o = e;
					r.has(o) || (r.add(o), !(a & 155648) && !this.is_skipped(o) && this.schedule(o, n));
				}
			}
		}
	}
	#m(t, n, r, i) {
		t.f ^= e;
		for (var a = t.first; a !== null;) {
			var o = a.f, s = !!(o & 96);
			if (!(s && o & 1024 || o & 139264 || this.#u(a)) && a.fn !== null) {
				s ? a.f ^= e : o & 4 ? n.push(a) : Kn(a) && hr(a);
				var c = a.first;
				if (c !== null) {
					a = c;
					continue;
				}
			}
			for (; a !== null;) {
				if ((a.f & 16512) == 128) {
					var l = a.b;
					l.is_pending && l.is_ready(this) && i.push(l);
				}
				var u = a.next;
				if (u !== null) {
					a = u;
					break;
				}
				a = a.parent;
			}
		}
	}
	#h() {
		for (var e = this.prev; e !== null; e = e.prev) if (!e.is_fork && this.#g(e)) return e;
		return null;
	}
	#g(e) {
		for (let t of this.current.keys()) if (e.current.has(t)) return !0;
		return !1;
	}
	#_(e) {
		for (let t of e.merge_requests) this.merge_requests.add(t);
		e.merge_requests.clear();
		for (let [t, n] of e.current) {
			if (!this.previous.has(t)) {
				let n = e.previous.get(t);
				n && this.previous.set(t, n);
			}
			this.current.set(t, n);
		}
		for (let [t, n] of e.async_deriveds) {
			let e = this.async_deriveds.get(t);
			e && e !== n && n.promise.then(e.resolve, e.reject), this.async_deriveds.set(t, n);
		}
		for (let [n, r] of e.records ?? []) if (!(n.f & 16)) {
			var t = this.records?.get(n);
			(this.records ??= /* @__PURE__ */ new Map()).set(n, r), e.records?.delete(n), Yn(n, t);
		}
		if (e.async_deriveds.clear(), e.#n.size > 0) {
			for (let [t, n] of e.#n) this.#n.set(t, (this.#n.get(t) ?? 0) + n);
			e.#n.clear();
		}
		if (e.#i.size > 0) {
			for (let [t, n] of e.#i) this.#v(t, n);
			e.#i.clear();
		}
		let n = () => e.discard();
		this.oncommit(n), this.ondiscard(n), e.merged = this, e.#T();
	}
	#v(e, t) {
		(t === 2048 || this.#i.get(e) !== 2048) && this.#i.set(e, t);
	}
	#y(r) {
		for (var i = 0; i < r.length; i += 1) {
			var a = r[i], o = a.f & (t | n);
			o !== 0 && (this.#v(a, a.dv === null ? n : o), O(a, e));
		}
	}
	capture(e, n, r, i = !1, a = null) {
		var o = this.previous.get(e), s = Qt(this, e);
		o === void 0 && (o = s?.previous.get(e), o === void 0 && e.v !== b && (o = {
			v: e.v,
			wv: e.wv,
			e: (e.f & f) !== 0,
			assigned: (e.f & m) !== 0
		}), o !== void 0 && this.previous.set(e, o)), B ? Pt(e) : o !== void 0 && (N?.reverted_values.set(e, o), N?.derived_cache.clear());
		var c = {
			v: n,
			wv: r ? e.wv : Vn(),
			e: i,
			assigned: !!(e.f & 2),
			async: (e.f & d) !== 0
		};
		this.current.set(e, c), P?.set(e, c), F?.delete(e), !this.is_fork && s !== null && s.previous.set(e, c), !this.is_fork && !r && s === null && $t(e, c), r || (Vt = null, Ht = 0, this.mark(e, t, a), Vt = null, St.size > 0 && !Ct && Dt());
	}
	deactivate() {
		M = jt = P = F = I = null;
	}
	flush() {
		var e = Nt(this.previous);
		try {
			if (this.#f(), It.size > 0) for (let e of It) It.delete(e), e.linked && !e.#c && e.#f();
		} finally {
			Bt = 0, Ft = null, Rt = null, zt = null, N = e.parent, this.deactivate();
		}
	}
	discard() {
		this.#x(this.#t);
		for (let e of this.async_deriveds.values()) e.reject(ft);
		this.#T(), this.#r?.resolve();
	}
	#b() {
		for (let i = j; i !== null; i = i.next) if (i !== this) {
			var e = i.id < this.id, t = [];
			for (let [r, a] of this.current) {
				var n = i.current.get(r);
				if (n !== void 0) {
					if (e && a.v !== n.v && !n.async) i.current.set(r, a);
					else continue;
				}
				t.push(r);
			}
			if (i.started && i.current.size !== 0) {
				var r = !0;
				for (let e of i.current.keys()) if (!this.current.has(e)) {
					r = !1;
					break;
				}
				r && e ? i.discard() : t.length > 0 && (i.#p(t), It.add(i));
			}
		}
		this.current.clear(), this.previous.clear();
	}
	commit_writes() {
		this.#b(), this.linked && this.prev !== null && this.#w();
	}
	increment(e) {
		var t = this.#n.get(e) ?? 0;
		this.#n.set(e, t + 1);
	}
	decrement(e) {
		var t = this.#n.get(e) ?? 0;
		t === 1 ? this.#n.delete(e) : this.#n.set(e, t - 1), this.#c || (this.#c = !0, E(() => {
			this.#c = !1, this.linked && this.flush();
		}));
	}
	oncommit(e) {
		this.#e.set(e, Yt?.size ? Yt : null);
	}
	ondiscard(e) {
		this.#t.set(e, Yt?.size ? Yt : null);
	}
	#x(e) {
		xr(() => {
			for (let [n, r] of e) if (r === null) n(this);
			else {
				var t = Nt();
				for (let [e, n] of r) t.reverted_values.has(e) && t.reverted_values.set(e, n);
				try {
					n(this);
				} finally {
					N = t.parent;
				}
			}
		}), e.clear();
	}
	settled() {
		return (this.#r ??= Ae()).promise;
	}
	static ensure() {
		if (M === null) {
			let e = M = new r();
			jt === null && !Lt && E(() => {
				e.started || e.flush();
			});
		}
		return M;
	}
	activate() {
		M = this, I = this, Wt !== this.id && (Wt = null), P = F = null;
	}
	get_record(e) {
		for (var t = this.records?.get(e), n = this.folded.length; t === void 0 && n--;) t = this.folded[n].records?.get(e);
		return t;
	}
	mark(e, r, i = null) {
		var a = e.reactions;
		if (a !== null) {
			var o = Xe(), s = a.length;
			if (Ht += s, Ht > 1e5 && Vt === null && (Vt = /* @__PURE__ */ new Set()), Vt !== null) {
				if (Vt.has(e)) return;
				Vt.add(e);
			}
			for (var c = 0; c < s; c++) {
				var l = a[c], u = l.f;
				if (o || l !== W) {
					var d = (u & t) === 0;
					if (u & 131072) this.is_fork || (d && O(l, r), St.add(l));
					else if (u & 2) {
						d && O(l, r);
						var f = l;
						F?.delete(f), this.mark(f, n, i);
					} else if (d) {
						var p = l;
						u & 16 && Jt !== null && (O(p, r), Jt.add(p)), i === null ? this.schedule(p, r) : (O(p, r), i.push(p));
					}
				}
			}
		}
	}
	schedule(e, t) {
		if (Ft = e, I !== null && I !== this && e !== V) this.#v(e, e.f & 2097152 ? t : n);
		else {
			if (jt !== this && V === null) {
				if (this.prev !== null || this.next !== null || this.is_fork) {
					this.#v(e, n);
					return;
				}
				t = n;
			}
			this.#S(e, t);
		}
	}
	#S(e, t) {
		e.f & 2048 || O(e, t), this.#a.push(e);
	}
	#C(e = !1) {
		var t = this.records;
		if (t !== null) {
			this.records = null;
			for (let [r, i] of t) {
				if (!(r.f & 16386)) {
					var n = !!(r.f & 4194304) && Qn(i) && !Qn(r);
					if (e && !n && (lr(r, i), r.f & 4194304)) for (let e = j; e !== null; e = e.next) e !== this && !e.records?.has(r) && e.async_deriveds.get(r)?.reject(ft);
					dr(r);
				}
				Yn(r, i);
			}
		}
	}
	#w() {
		var e = this.prev, t = j;
		e.next = this.next, this.next === null ? At = e : this.next.prev = e, this.prev = null, this.next = t, t.prev = j = this, this.id = t.id - 1;
	}
	#T() {
		if (this.linked) {
			var e = this.prev, t = this.next;
			e === null ? j = t : e.next = t, t === null ? At = e : t.prev = e, this.linked = !1, this.#C();
		}
	}
};
function Kt(e) {
	var t = Lt, n = I === M ? null : I;
	Lt = !0;
	try {
		var r;
		for (e && (Kt(), r = e());;) {
			if ($e(), M === null) return r;
			M.flush();
		}
	} finally {
		Lt = t, I = n;
	}
}
function qt() {
	try {
		Le();
	} catch (e) {
		Me(e, Ft);
	}
}
var Jt = null, Yt = null;
function Xt(e) {
	if ((e.f & 32772) != 4) return !1;
	for (var t = e.b; t !== null; t = t.parent) if (t.is_pending) return t.defer_effect(e), !0;
	return !1;
}
function Zt(e, t = null) {
	var n = e.length;
	if (n === 0) return t;
	for (var r = 0; r < n;) {
		var i = e[r++];
		if (!(i.f & 24576) && !M?.is_skipped(i) && !Xt(i) && Kn(i)) {
			Jt = /* @__PURE__ */ new Set();
			var a = Ln;
			if (hr(i), i.edges === null && i.first === null && i.nodes === null && i.teardown === null && i.ac === null && xn(i), Jt?.size > 0) {
				var o = N;
				t !== null && Nt(t);
				var s = Yt;
				Yt = new Map(t);
				try {
					for (let e of Jt) {
						if (e.f & 24576 || M?.is_skipped(e)) continue;
						let t = [e], n = e.parent;
						for (; n !== null;) Jt.has(n) && (Jt.delete(n), t.push(n)), n = n.parent;
						for (let e = t.length - 1; e >= 0; e--) {
							let n = t[e];
							n.f & 24576 || M?.is_skipped(n) || hr(n);
						}
					}
				} finally {
					Yt = s, Jt?.clear(), N = o;
				}
			}
			if (Ln !== a && M !== null) for (let [e, n] of M.current) n.wv > a && (t ??= /* @__PURE__ */ new Map()).set(e, n);
		}
	}
	return Jt = null, t;
}
function Qt(e, t) {
	for (var n = e.next; n !== null && (n.is_fork || !n.current.has(t));) n = n.next;
	return n;
}
function $t(e, t) {
	e.v = t.v, e.wv = t.wv, e.f = t.e ? e.f | f : e.f & ~f, e.f & 2 && (e.f |= m, ut(e));
}
function en(e) {
	var t = P, n = F, r = I;
	P = F = I = null;
	try {
		e();
	} finally {
		P = t, F = n, I = r;
	}
}
function tn(t, n = !1) {
	if (!(!n && t.f & 32 && t.f & 1024)) {
		O(t, e);
		for (var r = t.first; r !== null;) tn(r, n), r = r.next;
	}
}
// node_modules/svelte/src/internal/client/reactivity/effects.js
function nn(e) {
	W === null && (V === null && Ie(e), Fe()), B && Pe(e);
}
function rn(e, t) {
	var n = t.last;
	n === null ? t.last = t.first = e : (n.next = e, e.prev = n, t.last = e);
}
function L(e, n) {
	var i = W;
	i !== null && i.f & 8192 && (e |= r);
	var a = {
		ctx: T,
		deps: null,
		dv: null,
		edges: null,
		nodes: null,
		f: e | t | 512,
		first: null,
		fn: n,
		last: null,
		next: null,
		parent: i,
		b: i && i.b,
		prev: null,
		teardown: null,
		wv: 0,
		ac: null,
		r: rt
	}, s = a;
	if (e & 4) Rt === null ? Gt.ensure().schedule(a, t) : Rt.push(a);
	else if (n !== null) {
		try {
			hr(a);
		} catch (e) {
			throw z(a), e;
		}
		s.edges === null && s.teardown === null && s.nodes === null && s.first === s.last && !(s.f & 524288) && (s = s.first, e & 16 && e & 65536 && s !== null && (s.f |= o));
	}
	if (s !== null && (s.parent = i, i !== null && rn(s, i), V !== null && V.f & 2 && !(e & 64))) {
		var c = V;
		(c.effects ??= []).push(s);
	}
	return a;
}
function an() {
	return V !== null && !H;
}
function on(t) {
	let n = L(8, null);
	return O(n, e), n.teardown = t, n;
}
function sn(e) {
	nn("$effect");
	var t = W.f;
	if (!V && t & 32 && T !== null && !T.i) {
		var n = T;
		(n.e ??= []).push(e);
	} else return cn(e);
}
function cn(e) {
	return L(4 | c, e);
}
function ln(e) {
	return nn("$effect.pre"), L(8 | c, e);
}
function un(e) {
	Gt.ensure();
	let t = L(64 | s, e);
	return () => {
		z(t);
	};
}
function dn(e) {
	Gt.ensure();
	let t = L(64 | s, e);
	return (e = {}) => new Promise((n) => {
		e.outro ? Sn(t, () => {
			z(t), n(void 0);
		}) : (z(t), n(void 0));
	});
}
function fn(e) {
	return L(4, e);
}
function pn(e) {
	return L(d | s, e);
}
function mn(e, t = 0) {
	return L(8 | t, e);
}
function hn(e, t = [], n = [], r = []) {
	it(r, t, n, (t) => {
		L(8, () => {
			e(...t.map(Z));
		});
	});
}
function gn(e, t = 0) {
	return L(16 | t, e);
}
function R(e) {
	return L(32 | s, e);
}
function _n(e) {
	var t = e.teardown;
	if (t !== null) {
		let n = B, r = Mn, i = N, a = V;
		Nn(!0), U(null);
		try {
			t.call(null);
		} catch (t) {
			Me(t, e.parent);
		} finally {
			Nn(n, r), Mt(i), U(a);
		}
	}
}
function vn(e, t = !1) {
	var n = e.first;
	for (e.first = e.last = null; n !== null;) {
		er(n);
		var r = n.next;
		n.f & 64 ? n.parent = null : z(n, t), n = r;
	}
}
function yn(e) {
	for (var t = e.first; t !== null;) {
		var n = t.next;
		t.f & 32 || z(t), t = n;
	}
}
function z(e, t = !0) {
	var n = !1;
	try {
		(t || e.f & 262144) && e.nodes !== null && e.nodes.end !== null && (bn(e.nodes.start, e.nodes.end), n = !0), e.f |= a, vn(e, t && !n), mr(e);
		var r = e.nodes && e.nodes.t;
		if (r !== null) for (let e of r) e.stop();
		_n(e);
	} finally {}
	e.f ^= a, e.f |= 16384;
	var i = e.parent;
	i !== null && i.first !== null && xn(e), e.next = e.prev = e.teardown = e.ctx = e.deps = e.dv = e.edges = e.fn = e.nodes = e.ac = e.b = e.r = null;
}
function bn(e, t) {
	for (; e !== null;) {
		var n = e === t ? null : /* @__PURE__ */ Mr(e);
		qr(e), e = n;
	}
}
function xn(e) {
	var t = e.parent, n = e.prev, r = e.next;
	n !== null && (n.next = r), r !== null && (r.prev = n), t !== null && (t.first === e && (t.first = r), t.last === e && (t.last = n));
}
function Sn(e, t, n = !0) {
	var r = [];
	e.f |= 256, Cn(e, r, !0);
	var i = () => {
		n && z(e), t && t();
	}, a = r.length;
	if (a > 0) {
		var o = N, s = () => {
			if (!--a) {
				var e = N;
				try {
					o && (o.derived_cache.clear(), Mt(o)), i();
				} finally {
					o && Mt(e);
				}
			}
		};
		for (var c of r) c.out(s);
	} else i();
}
function Cn(e, t, n) {
	if (!(e.f & 8192)) {
		e.f ^= r;
		var i = e.nodes && e.nodes.t;
		if (i !== null) for (let e of i) (e.is_global || n) && t.push(e);
		for (var a = e.first; a !== null;) {
			var o = a.next;
			if (!(a.f & 64)) {
				var s = !!(a.f & 65536) || !!(a.f & 32) && !!(e.f & 16);
				Cn(a, t, s ? n : !1);
			}
			a = o;
		}
	}
}
function wn(e) {
	e.f &= -257, Tn(e, !0);
}
function Tn(e, t) {
	if (!(e.f & 256) && e.f & 8192) {
		e.f ^= r, e.f & 1024 || Gt.ensure().schedule(e, n);
		for (var i = e.first; i !== null;) {
			var a = i.next, o = !!(i.f & 65536) || !!(i.f & 32);
			Tn(i, o ? t : !1), i = a;
		}
		var s = e.nodes && e.nodes.t;
		if (s !== null) for (let e of s) (e.is_global || t) && e.in();
	}
}
function En(e, t) {
	if (e.nodes) try {
		for (var n = e.nodes.start, r = e.nodes.end; n !== null;) {
			var i = n === r ? null : /* @__PURE__ */ Mr(n);
			Wr(t, n), n = i;
		}
	} finally {}
}
// node_modules/svelte/src/internal/client/legacy.js
var Dn = null, On = !1;
function kn() {
	On || (On = !0, ii(document, "reset", (e) => {
		Promise.resolve().then(() => {
			if (!e.defaultPrevented) for (let t of e.target.elements) t[ie]?.();
		});
	}, { capture: !0 }));
}
// node_modules/svelte/src/internal/client/dom/elements/bindings/shared.js
function An(e) {
	var t = V, n = W;
	U(null), G(null);
	try {
		return e();
	} finally {
		U(t), G(n);
	}
}
function jn(e, t, n, r = n) {
	e.addEventListener(t, () => An(n));
	let i = e[ie];
	e[ie] = i ? () => {
		i(), r(!0);
	} : () => r(!0), kn();
}
// node_modules/svelte/src/internal/client/runtime.js
var B = !1, Mn = 0;
function Nn(e, t = Ln) {
	B = e, Mn = t;
}
var Pn = {
	v: void 0,
	wv: 0,
	e: !1,
	assigned: !1
}, V = null, H = !1;
function U(e) {
	V = e;
}
var W = null;
function G(e) {
	W = e;
}
var K = null;
function Fn(e) {
	V !== null && (V.f & 2097152 || V.f & 2) && (K ??= /* @__PURE__ */ new Set()).add(e);
}
var q = null, J = 0, Y = null;
function In(e) {
	Y = e;
}
var Ln = 1, Rn = 0, zn = Rn;
function Bn(e) {
	zn = e;
}
function Vn() {
	return ++Ln;
}
function Hn(e) {
	return P === null ? (vt(e), e.wv) : e.f & 2 ? yt(e).wv : (P.get(e) ?? e).wv;
}
function Un(e, t) {
	if (e !== null) {
		for (var n = 0; n < t.length; n++) if (Hn(e[n]) !== t[n]) return !1;
	}
	return !0;
}
function Wn(e, t, n = null) {
	if (e !== null) for (var r = 0; r < e.length; r++) {
		var i = e[r];
		if (i.f & 2) {
			var a = i;
			if (P === null ? vt(i) : a = yt(i), a.wv > t) {
				if (a === i ? i.f & 67108864 : !("dv" in a)) return !0;
				if (n === null) n = /* @__PURE__ */ new Set();
				else if (n.has(a)) continue;
				if (Wn(a.deps, t, n)) return !0;
				n.add(a);
			}
		} else if (Hn(i) > t) return !0;
	}
	return !1;
}
function Gn(e) {
	return !!(e.f & 4194320) && I?.get_record(e) || e;
}
function Kn(t) {
	var n = t.f;
	if (!(n & 6144)) return !1;
	if (n & 67108864) {
		if (Wn(t.deps, t.wv)) return !0;
	} else if (n & 2048) return !0;
	else {
		var r = Gn(t), i = r.deps, a = r.dv;
		if (a === null) return !0;
		if (P === null) for (var o = 0, s = a.length; o < s; o++) {
			var c = i[o];
			if (vt(c), c.wv !== a[o]) return !0;
		}
		else if (!Un(i, a)) return !0;
	}
	return n & 512 && O(t, e), !1;
}
function qn(e, r, i = !0) {
	var a = e.reactions;
	if (a !== null && !(K !== null && K.has(e))) for (var o = 0; o < a.length; o++) {
		var s = a[o];
		s.f & 2 ? qn(s, r, !1) : r === s && M.schedule(s, i ? t : n);
	}
}
var X = null;
function Jn(e) {
	e && An(() => e.abort(ae));
}
function Yn(e, t, n = !1) {
	if (t?.ac) {
		for (var r = j; r !== null; r = r.next) if (r.records?.get(e) === t && (!n || r !== I && !$n(M, r))) return;
		Jn(t.ac), t.ac = null;
	}
}
function Xn(e, t) {
	var n = M, r = !!(t & 2);
	if (!(r && B)) {
		var i = n === null || !n.is_fork;
		Yn(e, I?.records?.get(e), !0), (r ? P === null || i && Qn(e) : i) && Jn(e.ac);
		for (var a = j; a !== null; a = a.next) $n(n, a) && Yn(e, a.records?.get(e), !0);
	}
}
function Zn(e) {
	Jn(e.ac), e.ac = X;
}
function Qn({ deps: e, dv: t }) {
	return t === null || t.some((t, n) => e[n].wv !== t);
}
function $n(e, t) {
	return e !== null && !e.is_fork && !t.is_fork && t.id < e.id && (P === null || t.previous.size === 0 || e.folded.includes(t));
}
function er(e) {
	if (!(e.f & 134217728)) return !1;
	e.f ^= p, Jn(e.ac), e.ac = null;
	for (var t = j; t !== null; t = t.next) {
		var n = t.records?.get(e);
		n?.ac && (Jn(n.ac), n.ac = null);
	}
	return !0;
}
function tr(e) {
	return !(e & 4194304) && (e & 32784) != 32784 ? !1 : I !== null && I === M;
}
function nr(e) {
	let t = M;
	var n = q, r = J, a = Y, o = V, s = K, c = T, l = H, d = zn, f = e.f;
	q = null, J = 0, Y = null, V = f & 96 ? null : e, K = null, Ke(e.ctx), H = !1, zn = ++Rn;
	var p = X;
	X = null, f & 134217728 && Xn(e, f);
	try {
		e.f |= u;
		var m = e.fn, h = m();
		if (e.f |= i, rr(e, f, h, !1), Xe() && Y !== null && !H && (q !== null || J > 0) && !(e.f & 6146)) for (var g = 0; g < Y.length; g++) qn(Y[g], e);
		if (o !== null && o !== e) {
			if (Rn++, o.deps !== null) for (let e = 0; e < r; e += 1) o.deps[e].rv = Rn;
			if (n !== null) for (let e of n) e.rv = Rn;
			Y !== null && (a === null ? a = Y : a.push(...Y));
		}
		return h;
	} catch (t) {
		var ee = t;
		try {
			ee = je(t);
		} finally {
			rr(e, f, ee, ee === t);
		}
		return ee;
	} finally {
		var te = X?.signal;
		t !== null && te !== void 0 && te.addEventListener("abort", () => {
			if (M !== null) {
				let e = D(t);
				e !== M && e.linked && !e.is_fork && M.merge_requests.add(e);
			}
		}), e.f ^= u, q = n, J = r, Y = a, V = o, K = s, Ke(c), H = l, zn = d, X = p;
	}
}
function rr(e, t, n, r) {
	var i = e.deps, a = J + (q === null ? 0 : q.length), o = e.dv;
	if (e.f & 16384) Jn(X);
	else if (X !== null && !(e.f & 134217728) && (Jn(X), X = null), t & 2 && B) {
		for (var s = 0, c = 0; c < a; c++) {
			var l = c < J ? i[c] : q[c - J];
			s = Math.max(s, br(l));
		}
		Pn = {
			v: n,
			wv: s,
			e: r,
			assigned: (t & m) !== 0
		};
	} else if (t & 2 && P === null && j !== null && j.next !== null && or(e, t), q === null && P === null && o !== null && a === i?.length && e.edges === i && !(t & 4194320)) {
		for (var u = 0; u < a; u++) o[u] = i[u].wv;
		o.length !== a && (o.length = a), t & 2 && ir(e, n, r), (e.ac || X) && Zn(e);
	} else ar(e, t, a, n, r);
}
function ir(e, t, n) {
	var r = e.f & ~m;
	(n || r & 8388608 || !e.equals(t)) && (e.v = t, e.wv = Vn(), r = n ? r | f : r & ~f), e.f = r, ut(e);
}
function ar(e, t, n, r, i) {
	var a = tr(t);
	if (P !== null && t & 2) {
		var o = P.get(e);
		o !== void 0 && o.wv !== e.wv && (a = !0);
	}
	var s = e.deps, c = s;
	(q !== null || J !== s?.length) && (c = J === 0 ? q : s.slice(0, J).concat(q ?? []));
	for (var l = !a && P === null && e.dv !== null ? e.dv : [], u = 0; u < n; u++) {
		var d = c[u];
		l[u] = sr(d), P !== null && t & 2 && (l[u] !== d.wv || (d.f & 1026) == 2) && (a = !0);
	}
	l.length !== n && (l.length = n), !a && P !== null && t & 2 && or(e, t);
	var f = a || ur(e), p = an() && !!(e.f & 512), m = e.edges;
	if (f && m !== null) {
		if (q !== null) {
			e.edges = m = m.slice();
			for (d of q) _e.call(m, d) || (m.push(d), p && (d.reactions ??= []).push(e));
		}
	} else {
		if (m === s) {
			if (m !== null) for (u = J; u < m.length; u++) pr(e, m[u]);
			if (p && q !== null) for (d of q) (d.reactions ??= []).push(e);
		} else {
			var h = new Set(c);
			for (d of m) h.delete(d) || pr(e, d);
			if (p) for (d of h) (d.reactions ??= []).push(e);
		}
		e.edges = c;
	}
	if (a) {
		var g = I;
		(g.records ??= /* @__PURE__ */ new Map()).set(e, t & 2 ? {
			deps: c,
			dv: l,
			v: r,
			e: i,
			wv: cr(e, g, r, i),
			ac: X
		} : {
			deps: c,
			dv: l,
			ac: X
		});
	} else e.deps = c, e.dv = l, (e.ac || X) && Zn(e), t & 2 && (ir(e, r, i), I?.records?.delete(e));
}
function or(e, t) {
	var n = e.dv;
	if (!(n === null || n.length === 0 || t & 67108864)) {
		for (var r, i = e.ac, a = i !== null && M !== null && M.is_fork && !i.signal.aborted, o = j; o !== null; o = o.next) o !== I && !o.records?.has(e) && (i === null || a || $n(M, o)) && (r ??= {
			deps: e.deps,
			dv: n.slice(),
			v: e.v,
			wv: e.wv,
			e: (t & f) !== 0
		}, (o.records ??= /* @__PURE__ */ new Map()).set(e, r));
		a && r !== void 0 && (r.ac = i, e.ac = null);
	}
}
function sr(e) {
	return P === null ? e.wv : e.f & 2 ? F.get(e)?.wv ?? -1 : (P.get(e) ?? e).wv;
}
function cr(e, t, n, r) {
	if (!r) {
		var i = t.get_record(e);
		if (i !== void 0 && !i.e && e.equals.call(i, n)) return i.wv;
		if (!(e.f & 8388608) && e.equals(n)) return e.wv;
	}
	return Vn();
}
function lr(e, t) {
	if (e.deps = t.deps, e.dv = e.f & 2 ? t.dv.slice() : t.dv, e.f & 2) {
		var n = e;
		n.v = t.v, n.wv = t.wv, n.f = (t.e ? n.f | f : n.f & ~f) & ~m, ut(n);
	}
	Jn(e.ac), e.ac = t.ac ?? null, t.ac = null;
}
function ur(e) {
	for (var t = j; t !== null; t = t.next) if (t.records?.has(e)) return !0;
	return !1;
}
function dr(e) {
	var t = e.edges, n = e.deps;
	if (!(t === n || ur(e))) {
		for (var r of t) n !== null && _e.call(n, r) || pr(e, r);
		e.edges = n;
	}
}
function fr(e, t) {
	var n = e.reactions ??= [];
	_e.call(n, t) || n.push(t);
}
function pr(e, n) {
	let r = n.reactions;
	if (r !== null) {
		var i = ge.call(r, e);
		if (i !== -1) {
			var a = r.length - 1;
			a === 0 ? r = n.reactions = null : (r[i] = r[a], r.pop());
		}
	}
	if (r === null && n.f & 2 && (q === null || !_e.call(q, n))) {
		var o = n;
		if (o.f & 512 && (o.f ^= 512), o.v !== b && ut(o), er(o)) {
			O(o, t), o.dv = null;
			for (var s = j; s !== null; s = s.next) s.records?.delete(o);
			F?.delete(o);
		}
		bt(o), mr(o);
	}
}
function mr(e) {
	var t = e.edges;
	if (t !== null) for (var n = 0; n < t.length; n++) pr(e, t[n]);
}
function hr(t) {
	var n = t.f;
	if (!(n & 16384)) {
		O(t, e);
		var r = W;
		W = t;
		try {
			n & 16777232 ? yn(t) : vn(t), _n(t);
			var i = nr(t);
			t.teardown = typeof i == "function" ? i : null, t.wv = Ln;
		} finally {
			W = r;
		}
	}
}
async function gr() {
	await Promise.resolve(), Kt();
}
function Z(e) {
	var t = !!(e.f & 2);
	Dn?.add(e);
	var n = null;
	if (V !== null && !H && !(W !== null && W.f & 16384) && (K === null || !K.has(e))) {
		var r = V.deps;
		if (V.f & 2097152) e.rv < Rn && (e.rv = Rn, q === null && r !== null && r[J] === e ? J++ : q === null ? q = [e] : q.push(e));
		else {
			n = V;
			var a = V.edges;
			a !== null && _e.call(a, e) || (V.edges = a === null ? [e] : [...a, e]), fr(e, V);
		}
	}
	if (B) {
		var o = yr(e);
		if (o !== void 0) {
			if (o.e) throw o.v;
			return o.v;
		}
	}
	var s;
	if (t) {
		var c = e, l = !(c.f & 512) && !H && V !== null && !!(V.f & 512), u = !(c.f & i);
		l && (c.f |= 512), P === null ? vt(c) : s = yt(c), l && !u && (xt(c), vr(c));
	} else P !== null && (s = P.get(e));
	if (n !== null && _r(n, e, s === void 0 ? e.wv : s.wv), s !== void 0 && s !== e) {
		if (s.e) throw s.v;
		return s.v;
	}
	if (e.f & 8388608) throw e.v;
	return e.v;
}
function _r(e, t, n) {
	var r = Gn(e), i = r.deps;
	r.dv === null || i !== null && _e.call(i, t) || (r.deps = i === null ? [t] : [...i, t], r.dv.push(n));
}
function vr(e) {
	if (e.f |= 512, e.edges !== null) for (let t of e.edges) fr(t, e), t.f & 2 && !(t.f & 512) && (xt(t), vr(t));
}
function yr(e) {
	var t = e.wv > Mn ? void 0 : N?.reverted_values.get(e);
	if (!(e.f & 2)) return t;
	var n = e, r = (N ?? Nt()).derived_cache, i = r.get(n);
	if (i !== void 0) return i;
	var a = t ?? P?.get(n), o = a === void 0 ? (n.f & m) !== 0 : a.assigned, s = a === void 0 && !o ? n.dv : null, c = n.deps ?? [], l = o || s !== null, u = s?.length ?? c.length;
	a ??= {
		v: n.v,
		wv: n.wv,
		e: (n.f & f) !== 0,
		assigned: (n.f & m) !== 0
	};
	for (var d = 0; l && d < u; d++) {
		var p = br(c[d]);
		l = s === null ? p <= a.wv : p === s[d];
	}
	return l ? i = a : (_t(n), i = Pn, a.wv < i.wv && !a.e && !i.e && n.equals.call(a, i.v) && (i.wv = a.wv)), r.set(n, i), i;
}
function br(e) {
	return (yr(e) ?? P?.get(e) ?? e).wv;
}
function xr(e) {
	var t = H;
	try {
		return H = !0, e();
	} finally {
		H = t;
	}
}
function Sr(e) {
	if (!(typeof e != "object" || !e || e instanceof EventTarget)) {
		if (h in e) Cr(e);
		else if (!Array.isArray(e)) for (let t in e) {
			let n = e[t];
			typeof n == "object" && n && h in n && Cr(n);
		}
	}
}
function Cr(e, t = /* @__PURE__ */ new Set()) {
	if (typeof e == "object" && e && !(e instanceof EventTarget) && !t.has(e)) {
		t.add(e), e instanceof Date && e.getTime();
		for (let n in e) try {
			Cr(e[n], t);
		} catch {}
		let n = Te(e);
		if (n !== Object.prototype && n !== Array.prototype && n !== Map.prototype && n !== Set.prototype && n !== Date.prototype) {
			let t = Se(n);
			for (let n in t) {
				let r = t[n].get;
				if (r) try {
					r.call(e);
				} catch {}
			}
		}
	}
}
function wr(e) {
	if (typeof e != "object" || !e || h in e || g in e) return e;
	let t = Te(e);
	if (t !== Ce && t !== we) return e;
	var n = /* @__PURE__ */ new Map(), r = he(e), i = /* @__PURE__ */ Tt(0), a = null, o = zn, s = (e) => {
		if (zn === o) return e();
		var t = V, n = zn;
		U(null), Bn(o);
		var r = e();
		return U(t), Bn(n), r;
	};
	return r && n.set("length", /* @__PURE__ */ Tt(e.length, a)), new Proxy(e, {
		defineProperty(e, t, r) {
			"value" in r && r.configurable !== !1 && r.enumerable !== !1 && r.writable !== !1 || Be();
			var i = n.get(t);
			return i === void 0 ? s(() => {
				var e = /* @__PURE__ */ Tt(r.value, a);
				return n.set(t, e), e;
			}) : A(i, r.value, !0), !0;
		},
		deleteProperty(e, t) {
			var r = n.get(t);
			if (r === void 0) {
				if (t in e) {
					let e = s(() => /* @__PURE__ */ Tt(b, a));
					n.set(t, e), kt(i);
				}
			} else A(r, b), kt(i);
			return !0;
		},
		get(t, r, i) {
			if (r === h) return e;
			var o = n.get(r), c = r in t;
			if (o === void 0 && (!c || xe(t, r)?.writable) && (o = s(() => /* @__PURE__ */ Tt(wr(c ? t[r] : b), a)), n.set(r, o)), o !== void 0) {
				var l = Z(o);
				return l === b ? void 0 : l;
			}
			return Reflect.get(t, r, i);
		},
		getOwnPropertyDescriptor(e, t) {
			this.has?.(e, t);
			var r = Reflect.getOwnPropertyDescriptor(e, t), i = n.get(t);
			if (i !== void 0) {
				var a = Z(i);
				if (a === b) return;
				if (r && "value" in r) r.value = a;
				else return {
					enumerable: !0,
					configurable: !0,
					value: a,
					writable: !0
				};
			}
			return r;
		},
		has(e, t) {
			if (t === h) return !0;
			var r = n.get(t), i = r !== void 0 && r.v !== b || Reflect.has(e, t);
			return (r !== void 0 || (W !== null || V !== null) && (!i || xe(e, t)?.writable)) && (r === void 0 && (r = s(() => /* @__PURE__ */ Tt(i ? wr(e[t]) : b, a)), n.set(t, r)), Z(r) === b) ? !1 : i;
		},
		set(e, t, o, c) {
			var l = n.get(t), u = t in e;
			if (r && t === "length") for (var d = o; d < l.v; d += 1) {
				var f = n.get(d + "");
				f === void 0 ? d in e && (f = s(() => /* @__PURE__ */ Tt(b, a)), n.set(d + "", f)) : A(f, b);
			}
			if (l === void 0) (!u || xe(e, t)?.writable) && (l = s(() => /* @__PURE__ */ Tt(void 0, a)), A(l, wr(o)), n.set(t, l));
			else {
				u = l.v !== b;
				var p = s(() => wr(o));
				A(l, p);
			}
			var m = Reflect.getOwnPropertyDescriptor(e, t);
			if (m?.set && m.set.call(c, o), !u) {
				if (r && typeof t == "string") {
					var h = n.get("length"), g = Number(t);
					Number.isInteger(g) && g >= h.v && A(h, g + 1);
				}
				kt(i);
			}
			return !0;
		},
		ownKeys(e) {
			Z(i);
			var t = Reflect.ownKeys(e).filter((e) => {
				var t = n.get(e);
				return t === void 0 || t.v !== b;
			});
			for (var [r, a] of n) a.v !== b && !(r in e) && t.push(r);
			return t;
		},
		setPrototypeOf() {
			Ve();
		}
	});
}
var Tr, Er, Dr, Or;
function kr() {
	if (Tr === void 0) {
		Tr = window, Er = /Firefox/.test(navigator.userAgent);
		var e = Element.prototype, t = Node.prototype, n = Text.prototype;
		Dr = xe(t, "firstChild").get, Or = xe(t, "nextSibling").get, Ee(e) && (e[_] = void 0, e[ne] = null, e[v] = void 0, e.__e = void 0), Ee(n) && (n[re] = void 0);
	}
}
function Ar(e = "") {
	return document.createTextNode(e);
}
/*@__NO_SIDE_EFFECTS__*/
function jr(e) {
	return Dr.call(e);
}
/*@__NO_SIDE_EFFECTS__*/
function Mr(e) {
	return Or.call(e);
}
function Q(e, t) {
	if (!x) return /* @__PURE__ */ jr(e);
	var n = /* @__PURE__ */ jr(S);
	if (n === null) n = Wr(S, Ar());
	else if (t && Br(n) !== 3) {
		var r = Ar();
		return Gr(n, r), C(r), r;
	}
	return t && zr(n), C(n), n;
}
function Nr(e, t = !1) {
	if (!x) return /* @__PURE__ */ jr(e);
	var n = Q(e, t);
	return w(e), n;
}
function $(e, t = 1, n = !1) {
	let r = x ? S : e;
	for (var i; t--;) i = r, r = /* @__PURE__ */ Mr(r);
	if (!x) return r;
	if (n) {
		if (Br(r) !== 3) {
			var a = Ar();
			return r === null ? i && Kr(i, a) : Gr(r, a), C(a), a;
		}
		zr(r);
	}
	return C(r), r;
}
function Pr(e) {
	e.textContent = "";
}
function Fr() {
	return Yt !== null && !!(W.f & i);
}
function Ir(e, t, n) {
	return t == null || t === "http://www.w3.org/1999/xhtml" ? n ? document.createElement(e, { is: n }) : document.createElement(e) : n ? document.createElementNS(t, e, { is: n }) : document.createElementNS(t, e);
}
function Lr() {
	return document.createDocumentFragment();
}
function Rr(e, t, n = "") {
	if (t.startsWith("xlink:")) e.setAttributeNS("http://www.w3.org/1999/xlink", t, n);
	else return e.setAttribute(t, n);
}
function zr(e) {
	if (e.nodeValue.length < 65536) return;
	let t = e.nextSibling;
	for (; t !== null && Br(t) === 3;) t.remove(), e.nodeValue += t.nodeValue, t = e.nextSibling;
}
function Br(e) {
	if (e != null) return e.nodeType;
}
function Vr(e) {
	return e.nodeName;
}
function Hr(e) {
	return e.lastChild;
}
function Ur(e) {
	return e.parentNode;
}
function Wr(e, t) {
	return e.appendChild(t);
}
function Gr(e, t) {
	e.before(t);
}
function Kr(e, t) {
	e.after(t);
}
function qr(e) {
	e.remove();
}
function Jr(e, t) {
	return e.removeChild(t);
}
function Yr(e, t) {
	e.textContent = t;
}
function Xr(e, t) {
	e.nodeValue = t;
}
function Zr(e) {
	return e.nodeValue;
}
function Qr(e, t) {
	return e.getAttribute(t);
}
function $r(e, t) {
	e.removeAttribute(t);
}
function ei(e, t) {
	return e.hasAttribute(t);
}
function ti(e, t) {
	e.innerHTML = t;
}
function ni(e, t) {
	return e.cloneNode(t);
}
function ri(e, t) {
	return document.importNode(e, t);
}
function ii(e, t, n, r) {
	e.addEventListener(t, n, r);
}
function ai(e, t, n, r) {
	e.removeEventListener(t, n, r);
}
// node_modules/svelte/src/internal/flags/legacy.js
kr(), typeof window < "u" && ((globalThis.__svelte ??= {}).v ??= /* @__PURE__ */ new Set()).add("5"), Ge(), [.../* @__PURE__ */ "allowfullscreen.async.autofocus.autoplay.checked.controls.default.disabled.formnovalidate.indeterminate.inert.ismap.loop.multiple.muted.nomodule.novalidate.open.playsinline.readonly.required.reversed.seamless.selected.webkitdirectory.defer.disablepictureinpicture.disableremoteplayback".split(".")];
var oi = ["touchstart", "touchmove"];
function si(e) {
	return oi.includes(e);
}
// node_modules/svelte/src/internal/client/dom/elements/events.js
var ci = Symbol("events"), li = Symbol("propagation stopped at"), ui = /* @__PURE__ */ new Set(), di = /* @__PURE__ */ new Set();
function fi(e, t, n, r = {}) {
	var i = rt != null;
	function a(...e) {
		if (i) return An(() => n?.apply(this, e));
		var a = e[0];
		if (r.capture || vi.call(t, a), r.capture || a[li] !== t) return An(() => n?.call(this, a));
	}
	return !i && (e.startsWith("pointer") || e.startsWith("touch") || e === "wheel") ? (a.__removed = !1, E(() => {
		a.__removed || ii(t, e, a, r);
	})) : ii(t, e, a, r), a;
}
function pi(e, t, n, r, i) {
	var a = {
		capture: r,
		passive: i
	}, o = fi(e, t, n, a);
	rt == null && (t === document.body || t === window || t === document || t instanceof HTMLMediaElement) && on(() => {
		o.__removed = !0, ai(t, e, o, a);
	});
}
var mi = /* @__PURE__ */ new Map();
function hi(e) {
	var t = /* @__PURE__ */ new Set(), n = (n) => {
		for (var r = 0; r < n.length; r++) {
			var i = n[r];
			if (!t.has(i)) {
				t.add(i);
				var a = si(i);
				for (let t of [e, document]) {
					var o = mi.get(t);
					o === void 0 && (o = /* @__PURE__ */ new Map(), mi.set(t, o));
					var s = o.get(i);
					s === void 0 ? (t.addEventListener(i, vi, { passive: a }), o.set(i, 1)) : o.set(i, s + 1);
				}
			}
		}
	};
	return n(ve(ui)), di.add(n), () => {
		for (var r of t) for (let t of [e, document]) {
			var i = mi.get(t), a = i.get(r);
			--a == 0 ? (t.removeEventListener(r, vi), i.delete(r), i.size === 0 && mi.delete(t)) : i.set(r, a);
		}
		di.delete(n);
	};
}
var gi = null, _i = !1;
function vi(e) {
	var t = this, n = e.cancelBubble;
	if (!(n && e[li] === t)) {
		n || delete e[li];
		var r = t.ownerDocument, i = e.type, a = e.composedPath?.() || [], o = a[0] || e.target;
		gi = e, _i || (_i = !0, setTimeout(() => {
			_i = !1, gi = null;
		}));
		var s = 0, c = gi === e && e[ci];
		if (c) {
			var l = a.indexOf(c);
			if (l !== -1 && (t === document || t === window)) {
				e[ci] = t;
				return;
			}
			var u = a.indexOf(t);
			if (u === -1) return;
			l <= u && (s = l);
		}
		if (o = a[s] || e.target, o !== t) {
			be(e, "currentTarget", {
				configurable: !0,
				get() {
					return o || r;
				}
			});
			var d = V, f = W;
			U(null), G(null);
			try {
				for (var p, m = []; o !== null && o !== t;) {
					try {
						var h = o[ci]?.[i];
						h == null || o.disabled && e.target !== o || h.call(o, e);
					} catch (e) {
						p ? m.push(e) : p = e;
					}
					if (e.cancelBubble) {
						n || (e[li] = t);
						break;
					}
					s++, o = s < a.length ? a[s] : null;
				}
				if (p) {
					for (let e of m) queueMicrotask(() => {
						throw e;
					});
					throw p;
				}
			} finally {
				e[ci] = t, delete e.currentTarget, U(d), G(f);
			}
		}
	}
}
// node_modules/svelte/src/internal/client/dom/reconciler.js
var yi = globalThis?.window?.trustedTypes && /* @__PURE__ */ globalThis.window.trustedTypes.createPolicy("svelte-trusted-html", { createHTML: (e) => e });
function bi(e) {
	return yi?.createHTML(e) ?? e;
}
function xi(e) {
	var t = Ir("template");
	return ti(t, bi(e.replaceAll("<!>", "<!---->"))), t.content;
}
// node_modules/svelte/src/internal/client/dom/template.js
function Si(e, t) {
	var n = W;
	n.nodes === null && (n.nodes = {
		start: e,
		end: t,
		a: null,
		t: null
	});
}
/*#__NO_SIDE_EFFECTS__*/
function Ci(e, t) {
	var n = !!(t & 1), r = !!(t & 2), i, a = !e.startsWith("<!>");
	return () => {
		if (x) return Si(S, null), S;
		i === void 0 && (i = xi(a ? e : "<!>" + e), n || (i = /* @__PURE__ */ jr(i)));
		var t = r || Er ? ri(i, !0) : ni(i, !0);
		return n ? Si(/* @__PURE__ */ jr(t), Hr(t)) : Si(t, t), t;
	};
}
function wi(e, t) {
	if (x) {
		var n = W;
		n.f & 32768 && n.nodes.end !== null || (n.nodes.end = S), de();
	} else e !== null && Gr(e, t);
}
// node_modules/svelte/src/reactivity/create-subscriber.js
function Ti(e) {
	let t = 0, n = wt(0), r;
	return () => {
		an() && (Z(n), mn(() => (t === 0 && (r = xr(() => e(() => kt(n)))), t += 1, () => {
			E(() => {
				--t, t === 0 && (r?.(), r = void 0, kt(n));
			});
		})));
	};
}
// node_modules/svelte/src/internal/client/dom/blocks/boundary.js
var Ei = o | s;
function Di(e, t, n, r) {
	new Oi(e, t, n, r);
}
var Oi = class {
	parent;
	is_pending = !1;
	transform_error;
	#e;
	#t = x ? S : null;
	#n;
	#r;
	#i;
	#a = null;
	#o = null;
	#s = null;
	#c = null;
	#l = 0;
	#u = !1;
	#d = [];
	#f = /* @__PURE__ */ new Map();
	#p = null;
	#m = Ti(() => (this.#p = wt(this.#l), () => {
		this.#p = null;
	}));
	constructor(e, t, n, r) {
		this.#e = e, this.#n = t, this.#r = (e) => {
			var t = W;
			t.b = this, t.f |= 128, n(e);
		}, this.parent = W.b, this.transform_error = r ?? this.parent?.transform_error ?? ((e) => e), this.#i = gn(() => {
			if (x) {
				let e = me(this.#t);
				de();
				let t = e === "[!";
				if (e.startsWith("[?")) {
					let t = JSON.parse(e.slice(2));
					this.#g(t);
				} else t ? this.#y() : this.#h();
			} else this.#b();
		}, Ei), x && (this.#e = S);
	}
	#h() {
		try {
			this.#a = R(() => this.#r(this.#e));
		} catch (e) {
			this.error(e);
		}
	}
	#g(e) {
		let t = this.#n.failed, { reset: n, invoke_onerror: r } = this.#_(e);
		E(r), t && (this.#s = R(() => {
			t(this.#e, () => e, () => n);
		}));
	}
	#_(e) {
		var t = !1, n = !1;
		let r = () => {
			this.#v() || (t ? le() : (t = !0, n && Ue(), this.#s !== null && Sn(this.#s, () => {
				this.#s = null;
			}), this.#x(() => {
				this.#b();
			})));
		};
		return {
			reset: r,
			invoke_onerror: () => {
				if (!this.#v()) try {
					n = !0, this.#n.onerror?.(e, r), n = !1;
				} catch (e) {
					Me(e, this.#i && this.#i.parent);
				}
			}
		};
	}
	#v() {
		return !!(this.#i.f & 33570816);
	}
	#y() {
		let e = this.#n.pending;
		e && (this.is_pending = !0, this.#o = R(() => e(this.#e)), E(() => {
			if (!this.#v()) try {
				var e = this.#c = Lr(), t = Ar();
				Wr(e, t), this.#a = this.#x(() => {
					try {
						return R(() => this.#r(t));
					} catch (e) {
						try {
							this.error(e);
						} catch (e) {
							Me(e, this.#i.parent);
						}
						return null;
					}
				}), this.#a !== null && this.#f.size === 0 && (this.is_pending = !1, Gr(this.#e, e), this.#c = null, Sn(this.#o, () => {
					this.#o = null;
				}));
			} finally {}
		}));
	}
	#b() {
		try {
			if (this.is_pending = this.has_pending_snippet(), this.#l = 0, this.#a = R(() => {
				this.#r(this.#e);
			}), this.#f.size === 0) this.is_pending = !1;
			else {
				let t = this.#n.pending;
				if (t) {
					var e = this.#c = Lr();
					En(this.#a, e), this.#o = R(() => t(this.#e));
				}
			}
		} catch (e) {
			this.error(e);
		}
	}
	defer_effect(e) {
		this.#d.push(e);
	}
	has_pending_snippet() {
		return !!this.#n.pending;
	}
	#x(e) {
		var t = W, n = V, r = T;
		G(this.#i), U(this.#i), Ke(this.#i.ctx);
		try {
			return Gt.ensure(), e();
		} finally {
			G(t), U(n), Ke(r);
		}
	}
	is_ready(e) {
		if (e.is_fork && this.#f.size > 0) return !1;
		for (let [t, n] of this.#f) if (!t.is_fork) {
			for (let t of n.keys()) if (e.is_blocked_by(t, this.#a)) return !1;
		}
		return !0;
	}
	reveal(e) {
		this.is_pending = !1;
		for (let n of this.#d) O(n, t), e.push(n);
		if (this.#d.length = 0, this.#o && Sn(this.#o, () => {
			this.#o = null;
		}), this.#c) try {
			Gr(this.#e, this.#c), this.#c = null;
		} finally {}
	}
	increment(e, t) {
		var n = this.#f.get(t);
		n === void 0 && this.#f.set(t, n = /* @__PURE__ */ new Map());
		var r = n.get(e) ?? 0;
		n.set(e, r + 1);
	}
	decrement(e, t) {
		var r = this.#f.get(t), i = r.get(e);
		i === 1 ? (r.delete(e), r.size === 0 && this.#f.delete(t), E(() => {
			this.is_pending && !this.#v() && Gt.ensure().schedule(this.#i, n);
		})) : r.set(e, i - 1);
	}
	update_effect_pending(e) {
		this.#l += e, !this.#p || this.#u || (this.#u = !0, E(() => {
			this.#u = !1, this.#p && Et(this.#p, this.#l);
		}));
	}
	get_effect_pending() {
		return this.#m(), Z(this.#p);
	}
	error(e) {
		if (e === y || !this.#n.onerror && !this.#n.failed) throw e;
		M?.is_fork ? (this.#a && M.skip_effect(this.#a), this.#o && M.skip_effect(this.#o), this.#s && M.skip_effect(this.#s), M.oncommit(() => {
			this.#v() || this.#S(e);
		})) : this.#S(e);
	}
	#S(e) {
		this.#a &&= (z(this.#a), null), this.#o &&= (z(this.#o), null), this.#s &&= (z(this.#s), null), x && (C(this.#t), fe(), C(pe()));
		let t = this.#n.failed, n = (e) => {
			if (this.#v()) return;
			let { reset: n, invoke_onerror: r } = this.#_(e);
			r(), t && !this.#v() && (this.#s = this.#x(() => {
				try {
					return R(() => {
						var r = W;
						r.b = this, r.f |= 128, t(this.#e, () => e, () => n);
					});
				} catch (e) {
					return Me(e, this.#i.parent), null;
				}
			}));
		};
		E(() => {
			if (!this.#v()) {
				var t;
				try {
					t = this.transform_error(e);
				} catch (e) {
					Me(e, this.#i && this.#i.parent);
					return;
				}
				typeof t == "object" && t && typeof t.then == "function" ? t.then(n, (e) => Me(e, this.#i && this.#i.parent)) : n(t);
			}
		});
	}
};
function ki(e, t) {
	var n = t == null ? "" : typeof t == "object" ? `${t}` : t;
	n !== (e[re] ??= Zr(e)) && (e[re] = n, Xr(e, `${n}`));
}
function Ai(e, t) {
	return Mi(e, t);
}
function ji(e, t) {
	t.intro = t.intro ?? !1;
	let n = t.target, r = x, i = S;
	try {
		for (var a = /* @__PURE__ */ jr(n); a && (Br(a) !== 8 || Zr(a) !== "[");) a = /* @__PURE__ */ Mr(a);
		if (!a) throw y;
		ue(!0), C(a);
		let r = Mi(e, {
			...t,
			anchor: a
		});
		return ue(!1), r;
	} catch (r) {
		if (r instanceof Error && r.message.split("\n").some((e) => e.startsWith("https://svelte.dev/e/"))) throw r;
		return r !== y && console.warn("Failed to hydrate: ", r), t.recover === !1 && Re(), Pr(n), ue(!1), Ai(e, t);
	} finally {
		ue(r), C(i);
	}
}
function Mi(e, t) {
	return Ni(e, t);
}
function Ni(e, { target: t, anchor: n, props: r = {}, events: i, context: a, intro: o = !0, transformError: s, renderer: c }) {
	var l = void 0, u = dn(() => {
		var o = n ?? Wr(t, Ar());
		Di(o, { pending: () => {} }, (t) => {
			qe({});
			var n = T;
			if (a && (n.c = a), i && (r.$$events = i), x && Si(t, null), l = e(t, r) || Ye(), x && (W.nodes.end = S, S === null || Br(S) !== 8 || Zr(S) !== "]")) throw ce(), y;
			Je();
		}, s);
		var u = c ? null : hi(t);
		return () => {
			if (u?.(), o !== n) {
				var e = Ur(o);
				e && Jr(e, o);
			}
		};
	});
	return Pi.set(l, u), l;
}
var Pi = /* @__PURE__ */ new WeakMap();
function Fi(e, t) {
	let n = Pi.get(e);
	return n ? (Pi.delete(e), n(t)) : Promise.resolve();
}
// node_modules/svelte/src/internal/client/dom/blocks/branches.js
var Ii = class {
	anchor;
	#e = /* @__PURE__ */ new Map();
	#t = /* @__PURE__ */ new Map();
	#n = /* @__PURE__ */ new Map();
	#r = /* @__PURE__ */ new Set();
	#i = !0;
	#a = null;
	constructor(e, t = !0) {
		this.anchor = e, this.#i = t, this.#a = rt;
	}
	#o = (e) => {
		if (this.#e.has(e)) try {
			var t = this.#e.get(e), n = this.#t.get(t);
			if (n) wn(n), this.#r.delete(t);
			else {
				var r = this.#n.get(t);
				r && (wn(r.effect), this.#t.set(t, r.effect), this.#n.delete(t), qr(Hr(r.fragment)), Gr(this.anchor, r.fragment), n = r.effect, n.f &= ~l);
			}
			this.#s(e);
			for (let [e, r] of this.#t) {
				if (e === t || this.#r.has(e)) continue;
				let i = () => {
					if (Array.from(this.#e.values()).includes(e)) {
						var t = Lr();
						En(r, t), Wr(t, Ar()), this.#n.set(e, {
							effect: r,
							fragment: t
						});
					} else z(r);
					this.#r.delete(e), this.#t.delete(e);
				};
				this.#i || !n ? (this.#r.add(e), Sn(r, i, !1)) : i();
			}
		} finally {}
	};
	#s = (e) => {
		for (let t of this.#e.keys()) t !== e && t.linked || this.#e.delete(t);
		let t = Array.from(this.#e.values());
		for (let [e, n] of this.#n) t.includes(e) || (z(n.effect), this.#n.delete(e));
	};
	ensure(e, t) {
		var n = M, r = Fr();
		if (t && !this.#t.has(e) && !this.#n.has(e)) {
			if (r) {
				var i = Lr(), a = Ar();
				Wr(i, a);
				var o = R(() => t(a));
				o.f |= l, n.unskip_new_effect(o), this.#n.set(e, {
					effect: o,
					fragment: i
				});
			} else this.#t.set(e, R(() => t(this.anchor)));
		}
		if (this.#e.set(n, e), r) {
			for (let [t, r] of this.#t) t === e ? n.unskip_effect(r) : n.skip_effect(r);
			for (let [t, r] of this.#n) t === e ? n.unskip_effect(r.effect) : n.skip_effect(r.effect);
			n.oncommit(this.#o), n.ondiscard(this.#s);
		} else x && (this.anchor = S), this.#o(n);
	}
};
function Li(e) {
	T === null && Ne("onMount"), We && T.l !== null ? Ri(T).m.push(e) : sn(() => {
		let t = xr(e);
		if (typeof t == "function") return t;
	});
}
function Ri(e) {
	var t = e.l;
	return t.u ??= {
		a: [],
		b: [],
		m: []
	};
}
// node_modules/svelte/src/internal/client/dom/blocks/if.js
function zi(e, t, n = !1) {
	var r;
	x && (r = S, de());
	var i = new Ii(e), a = n ? o : 0;
	function s(e, t) {
		if (x) {
			var n = me(r);
			if (e !== parseInt(n.substring(1))) {
				var a = pe();
				C(a), i.anchor = a, ue(!1), i.ensure(e, t), ue(!0);
				return;
			}
		}
		i.ensure(e, t);
	}
	gn(() => {
		var e = !1;
		t((t, n = 0) => {
			e = !0, s(n, t);
		}), e || s(-1, null);
	}, a);
}
// node_modules/svelte/src/internal/client/dom/css.js
function Bi(e, t) {
	fn(() => {
		e = W?.parent?.nodes?.start ?? e;
		var n = e.getRootNode(), r = n.host ? n : n.head ?? n.ownerDocument.head;
		if (!r.querySelector("#" + t.hash)) {
			let e = Ir("style");
			e.id = t.hash, Yr(e, t.code), Wr(r, e);
		}
	});
}
// node_modules/svelte/src/internal/client/dom/elements/attributes.js
var Vi = Symbol("is custom element"), Hi = Symbol("is html"), Ui = oe ? "link" : "LINK";
function Wi(e) {
	if (x) {
		var t = !1, n = () => {
			if (!t) {
				if (t = !0, ei(e, "value")) {
					var n = e.value;
					Gi(e, "value", null), e.value = n;
				}
				if (ei(e, "checked")) {
					var r = e.checked;
					Gi(e, "checked", null), e.checked = r;
				}
			}
		};
		e[ie] = n, E(n), kn();
	}
}
function Gi(e, t, n, r) {
	var i = Ki(e);
	if (!(x && (i[t] = Qr(e, t), t === "src" || t === "srcset" || t === "href" && Vr(e) === Ui))) {
		var a = i[t];
		a !== (i[t] = n) && (t === "loading" && (e[te] = n), n == null ? $r(e, t) : typeof n != "string" && Ji(e).has(t) ? e[t] = n : (!x || typeof n != "number" && typeof n != "boolean" || a !== String(n)) && Rr(e, t, n));
	}
}
function Ki(e) {
	return e[ne] ??= {
		[Vi]: Vr(e).includes("-"),
		[Hi]: rt == null && e.namespaceURI === "http://www.w3.org/1999/xhtml"
	};
}
var qi = /* @__PURE__ */ new Map();
function Ji(e) {
	var t = Qr(e, "is") || Vr(e), n = qi.get(t);
	if (n) return n;
	qi.set(t, n = /* @__PURE__ */ new Set());
	for (var r, i = e, a = Element.prototype; a !== i;) {
		for (var o in r = Se(i), r) r[o].set && o !== "innerHTML" && o !== "textContent" && o !== "innerText" && n.add(o);
		i = Te(i);
	}
	return n;
}
// node_modules/svelte/src/internal/client/dom/elements/bindings/input.js
function Yi(e, t, n = t) {
	var r = /* @__PURE__ */ new WeakSet();
	jn(e, "input", async (i) => {
		var a = i ? e.defaultValue : e.value;
		if (a = Xi(e) ? Zi(a) : a, n(a), M !== null && r.add(M), await gr(), a !== (a = t())) {
			var o = e.selectionStart, s = e.selectionEnd, c = e.value.length;
			if (e.value = a ?? "", s !== null) {
				var l = e.value.length;
				o === s && s === c && l > c ? (e.selectionStart = l, e.selectionEnd = l) : (e.selectionStart = o, e.selectionEnd = Math.min(s, l));
			}
		}
	}), (x && e.defaultValue !== e.value || xr(t) == null && e.value) && (n(Xi(e) ? Zi(e.value) : e.value), M !== null && r.add(M)), mn(() => {
		var n = t();
		e === document.activeElement && r.has(I) || Xi(e) && n === Zi(e.value) || (e.type !== "date" || n || e.value) && n !== e.value && (e.value = n ?? "");
	});
}
function Xi(e) {
	var t = e.type;
	return t === "number" || t === "range";
}
function Zi(e) {
	return e === "" ? null : +e;
}
// node_modules/svelte/src/internal/client/dom/legacy/lifecycle.js
function Qi(e = !1) {
	let t = T, n = t.l.u;
	if (!n) return;
	let r = () => Sr(t.s);
	if (e) {
		let e = 0, n = {}, i = /* @__PURE__ */ dt(() => {
			let r = !1, i = t.s;
			for (let e in i) i[e] !== n[e] && (n[e] = i[e], r = !0);
			return r && e++, e;
		});
		r = () => Z(i);
	}
	n.b.length && ln(() => {
		$i(t, r), ke(n.b);
	}), sn(() => {
		let e = xr(() => n.m.map(Oe));
		return () => {
			for (let t of e) typeof t == "function" && t();
		};
	}), n.a.length && sn(() => {
		$i(t, r), ke(n.a);
	});
}
function $i(e, t) {
	if (e.l.s) for (let t of e.l.s) Z(t);
	t();
}
// node_modules/svelte/src/internal/client/reactivity/store.js
var ea = !1;
function ta(e) {
	var t = ea;
	try {
		return ea = !1, [e(), ea];
	} finally {
		ea = t;
	}
}
// node_modules/svelte/src/internal/client/reactivity/props.js
function na(e, t, n, r) {
	var i = !We || !!(n & 2), a = !!(n & 8), o = !!(n & 16), s = r, c = !0, l = void 0, u = () => o && i ? (l ??= /* @__PURE__ */ dt(r), Z(l)) : (c && (c = !1, s = o ? xr(r) : r), s);
	let d;
	if (a) {
		var f = h in e || ee in e;
		d = xe(e, t)?.set ?? (f && t in e ? (n) => e[t] = n : void 0);
	}
	var p, m = !1;
	a ? [p, m] = ta(() => e[t]) : p = e[t], p === void 0 && r !== void 0 && (p = u(), d && (i && ze(t), d(p)));
	var g = i ? () => {
		var n = e[t];
		return n === void 0 ? u() : (c = !0, n);
	} : () => {
		var n = e[t];
		return n !== void 0 && (s = void 0), n === void 0 ? s : n;
	};
	if (i && !(n & 4)) return g;
	if (d) {
		var te = e.$$legacy;
		return (function(e, t) {
			return arguments.length > 0 ? ((!i || !t || te || m) && d(t ? g() : e), e) : g();
		});
	}
	var ne = !1, _ = (n & 1 ? dt : ht)(() => (ne = !1, g()));
	a && Z(_);
	var v = W;
	return (function(e, t) {
		if (arguments.length > 0) {
			let n = t ? Z(_) : i && a ? wr(e) : e;
			return A(_, n), ne = !0, s !== void 0 && (s = n), e;
		}
		return B && ne || v.f & 16384 ? _.v : Z(_);
	});
}
// node_modules/svelte/src/legacy/legacy-client.js
function ra(e) {
	return new ia(e);
}
var ia = class {
	#e;
	#t;
	constructor(e) {
		var t = /* @__PURE__ */ new Map(), n = (e, n) => {
			var r = /* @__PURE__ */ k(n, !1, !1);
			return t.set(e, r), r;
		};
		let r = new Proxy({
			...e.props || {},
			$$events: {}
		}, {
			get(e, r) {
				return Z(t.get(r) ?? n(r, Reflect.get(e, r)));
			},
			has(e, r) {
				return r === ee || (Z(t.get(r) ?? n(r, Reflect.get(e, r))), Reflect.has(e, r));
			},
			set(e, r, i) {
				return A(t.get(r) ?? n(r, i), i), Reflect.set(e, r, i);
			}
		}), i = {
			target: e.target,
			anchor: e.anchor,
			props: r,
			context: e.context,
			intro: e.intro ?? !1,
			recover: e.recover,
			transformError: e.transformError
		};
		this.#t = e.hydrate ? ji(e.component, i) : Ai(e.component, i), e?.props?.$$host && e.sync !== !1 || Kt(), this.#e = r.$$events;
		for (let e of Object.keys(this.#t)) e !== "$set" && e !== "$destroy" && e !== "$on" && be(this, e, {
			get() {
				return this.#t[e];
			},
			set(t) {
				this.#t[e] = t;
			},
			enumerable: !0
		});
		this.#t.$set = (e) => {
			Object.assign(r, e);
		}, this.#t.$destroy = () => {
			Fi(this.#t);
		};
	}
	$set(e) {
		this.#t.$set(e);
	}
	$on(e, t) {
		this.#e[e] = this.#e[e] || [];
		let n = (...e) => t.call(this, ...e);
		return this.#e[e].push(n), () => {
			this.#e[e] = this.#e[e].filter((e) => e !== n);
		};
	}
	$destroy() {
		this.#t.$destroy();
	}
}, aa;
typeof HTMLElement == "function" && (aa = class extends HTMLElement {
	$$ctor;
	$$s;
	$$c;
	$$cn = !1;
	$$d = {};
	$$r = !1;
	$$p_d = {};
	$$l = {};
	$$l_u = /* @__PURE__ */ new Map();
	$$me;
	$$shadowRoot = null;
	constructor(e, t, n) {
		super(), this.$$ctor = e, this.$$s = t, n && (this.$$shadowRoot = this.attachShadow(n));
	}
	addEventListener(e, t, n) {
		if (this.$$l[e] = this.$$l[e] || [], this.$$l[e].push(t), this.$$c) {
			let n = this.$$c.$on(e, t);
			this.$$l_u.set(t, n);
		}
		super.addEventListener(e, t, n);
	}
	removeEventListener(e, t, n) {
		if (super.removeEventListener(e, t, n), this.$$c) {
			let e = this.$$l_u.get(t);
			e && (e(), this.$$l_u.delete(t));
		}
	}
	async connectedCallback() {
		if (this.$$cn = !0, !this.$$c) {
			if (await Promise.resolve(), !this.$$cn || this.$$c) return;
			function e(e) {
				return (t) => {
					let n = Ir("slot");
					e !== "default" && (n.name = e), wi(t, n);
				};
			}
			let t = {}, n = sa(this);
			for (let r of this.$$s) r in n && (r === "default" && !this.$$d.children ? (this.$$d.children = e(r), t.default = !0) : t[r] = e(r));
			for (let e of this.attributes) {
				let t = this.$$g_p(e.name);
				t in this.$$d || (this.$$d[t] = oa(t, e.value, this.$$p_d, "toProp"));
			}
			for (let e in this.$$p_d) !(e in this.$$d) && this[e] !== void 0 && (this.$$d[e] = this[e], delete this[e]);
			this.$$c = ra({
				component: this.$$ctor,
				target: this.$$shadowRoot || this,
				props: {
					...this.$$d,
					$$slots: t,
					$$host: this
				}
			}), this.$$me = un(() => {
				mn(() => {
					this.$$r = !0;
					for (let e of ye(this.$$c)) {
						if (!this.$$p_d[e]?.reflect) continue;
						this.$$d[e] = this.$$c[e];
						let t = oa(e, this.$$d[e], this.$$p_d, "toAttribute");
						t == null ? this.removeAttribute(this.$$p_d[e].attribute || e) : this.setAttribute(this.$$p_d[e].attribute || e, t);
					}
					this.$$r = !1;
				});
			});
			for (let e in this.$$l) for (let t of this.$$l[e]) {
				let n = this.$$c.$on(e, t);
				this.$$l_u.set(t, n);
			}
			this.$$l = {};
		}
	}
	attributeChangedCallback(e, t, n) {
		this.$$r || (e = this.$$g_p(e), this.$$d[e] = oa(e, n, this.$$p_d, "toProp"), this.$$c?.$set({ [e]: this.$$d[e] }));
	}
	disconnectedCallback() {
		this.$$cn = !1, Promise.resolve().then(() => {
			!this.$$cn && this.$$c && (this.$$c.$destroy(), this.$$me(), this.$$c = void 0);
		});
	}
	$$g_p(e) {
		return ye(this.$$p_d).find((t) => this.$$p_d[t].attribute === e || !this.$$p_d[t].attribute && t.toLowerCase() === e) || e;
	}
});
function oa(e, t, n, r) {
	let i = n[e]?.type;
	if (t = i === "Boolean" && typeof t != "boolean" ? t != null : t, !r || !n[e]) return t;
	if (r === "toAttribute") switch (i) {
		case "Object":
		case "Array": return t == null ? null : JSON.stringify(t);
		case "Boolean": return t ? "" : null;
		case "Number": return t ?? null;
		default: return t;
	}
	else switch (i) {
		case "Object":
		case "Array": return t && JSON.parse(t);
		case "Boolean": return t;
		case "Number": return t == null ? t : +t;
		default: return t;
	}
}
function sa(e) {
	let t = {};
	return e.childNodes.forEach((e) => {
		t[e.slot || "default"] = !0;
	}), t;
}
function ca(e, t, n, r, i, a) {
	let o = class extends aa {
		constructor() {
			super(e, n, i), this.$$p_d = t;
		}
		static get observedAttributes() {
			return ye(t).map((e) => (t[e].attribute || e).toLowerCase());
		}
	};
	return ye(t).forEach((e) => {
		be(o.prototype, e, {
			get() {
				return this.$$c && e in this.$$c ? this.$$c[e] : this.$$d[e];
			},
			set(n) {
				n = oa(e, n, t), this.$$d[e] = n;
				var r = this.$$c;
				r && (xe(r, e)?.get ? r[e] = n : r.$set({ [e]: n }));
			}
		});
	}), r.forEach((e) => {
		be(o.prototype, e, { get() {
			return this.$$c?.[e];
		} });
	}), a && (o = a(o)), e.element = o, o;
}
// NavidromeCard.svelte
var la = /* @__PURE__ */ Ci("<span class=\"status-badge active svelte-6qi2q9\">● Active</span>"), ua = /* @__PURE__ */ Ci("<span class=\"status-badge success svelte-6qi2q9\">✓ Authenticated</span>"), da = /* @__PURE__ */ Ci("<span class=\"status-badge success svelte-6qi2q9\">● Connected</span>"), fa = /* @__PURE__ */ Ci("<span class=\"status-badge warning svelte-6qi2q9\">⚠ Disconnected</span>"), pa = /* @__PURE__ */ Ci("<div class=\"loading-state svelte-6qi2q9\">Loading...</div>"), ma = /* @__PURE__ */ Ci("<button class=\"btn-ghost svelte-6qi2q9\"> </button>"), ha = /* @__PURE__ */ Ci("<div class=\"settings-section svelte-6qi2q9\"><h3 class=\"section-title svelte-6qi2q9\">Server Configuration</h3> <div class=\"form-grid svelte-6qi2q9\"><label class=\"form-field svelte-6qi2q9\"><span class=\"field-label svelte-6qi2q9\">Server URL</span> <input type=\"text\" placeholder=\"http://192.168.1.100:4533\" class=\"input-field svelte-6qi2q9\"/> <span class=\"helper-text svelte-6qi2q9\">Enter your Navidrome server URL (include port, typically :4533)</span></label> <label class=\"form-field svelte-6qi2q9\"><span class=\"field-label svelte-6qi2q9\">Username</span> <input type=\"text\" placeholder=\"Enter username\" class=\"input-field svelte-6qi2q9\"/></label> <label class=\"form-field svelte-6qi2q9\"><span class=\"field-label svelte-6qi2q9\">Password</span> <div class=\"password-wrapper svelte-6qi2q9\"><input class=\"input-field svelte-6qi2q9\"/> <button type=\"button\" class=\"toggle-visibility svelte-6qi2q9\" aria-label=\"Toggle password visibility\"> </button></div></label> <div class=\"actions-row svelte-6qi2q9\"><button class=\"btn-primary svelte-6qi2q9\"> </button> <!> <!></div></div></div>"), ga = /* @__PURE__ */ Ci("<section class=\"plugin-card svelte-6qi2q9\"><div class=\"card-header svelte-6qi2q9\"><div class=\"header-left svelte-6qi2q9\"><h2 class=\"card-title svelte-6qi2q9\">Navidrome</h2> <div class=\"badges svelte-6qi2q9\"><!> <!> <!></div></div> <button class=\"btn-ghost svelte-6qi2q9\"> </button></div> <!></section>"), _a = {
	hash: "svelte-6qi2q9",
	code: ".plugin-card.svelte-6qi2q9 {background:var(--bg-surface, #0f172a);backdrop-filter:blur(12px);border:1px solid var(--border-subtle, #1e293b);border-radius:var(--radius, 12px);padding:24px;margin-bottom:24px;color:var(--text-primary, #f8fafc);}.card-header.svelte-6qi2q9 {display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;padding-bottom:12px;border-bottom:1px solid var(--border-subtle, #1e293b);}.header-left.svelte-6qi2q9 {display:flex;align-items:center;gap:16px;}.card-title.svelte-6qi2q9 {margin:0;font-size:20px;font-weight:700;}.badges.svelte-6qi2q9 {display:flex;gap:8px;}.status-badge.svelte-6qi2q9 {font-size:10px;padding:2px 8px;border-radius:4px;font-weight:700;}.status-badge.active.svelte-6qi2q9 {background:rgba(20, 184, 166, 0.15);color:var(--color-primary, #14b8a6);}.status-badge.success.svelte-6qi2q9 {background:rgba(34, 197, 94, 0.15);color:#22c55e;}.status-badge.warning.svelte-6qi2q9 {background:rgba(234, 179, 8, 0.15);color:#eab308;}.btn-ghost.svelte-6qi2q9 {padding:8px 16px;background:rgba(255, 255, 255, 0.05);border:1px solid rgba(255, 255, 255, 0.1);color:var(--text-primary);border-radius:8px;font-size:13px;cursor:pointer;transition:all 0.2s;}.btn-ghost.svelte-6qi2q9:hover {background:rgba(255, 255, 255, 0.1);}.btn-primary.svelte-6qi2q9 {padding:10px 20px;background:var(--color-primary, #14b8a6);color:var(--bg-canvas, #000000);border:none;border-radius:8px;font-weight:600;cursor:pointer;transition:all 0.2s;}.btn-primary.svelte-6qi2q9:hover {opacity:0.9;}.loading-state.svelte-6qi2q9 {padding:24px;text-align:center;color:var(--text-secondary, #94a3b8);}.settings-section.svelte-6qi2q9 {margin-top:16px;}.section-title.svelte-6qi2q9 {margin:0 0 16px 0;font-size:16px;font-weight:600;}.form-grid.svelte-6qi2q9 {display:flex;flex-direction:column;gap:16px;}.form-field.svelte-6qi2q9 {display:flex;flex-direction:column;gap:6px;}.field-label.svelte-6qi2q9 {font-size:13px;color:var(--text-secondary, #94a3b8);}.input-field.svelte-6qi2q9 {width:100%;padding:10px 14px;background:var(--bg-surface-elevated, #1e293b);border:1px solid var(--border-subtle, #334155);border-radius:8px;color:var(--text-primary, #f8fafc);font-size:14px;transition:all 0.2s;}.input-field.svelte-6qi2q9:focus {outline:none;border-color:var(--color-primary, #14b8a6);box-shadow:0 0 0 2px rgba(20, 184, 166, 0.1);}.password-wrapper.svelte-6qi2q9 {position:relative;display:flex;align-items:center;}.toggle-visibility.svelte-6qi2q9 {position:absolute;right:12px;background:none;border:none;cursor:pointer;opacity:0.6;color:var(--text-primary, #f8fafc);}.helper-text.svelte-6qi2q9 {font-size:11px;color:var(--text-secondary, #94a3b8);}.actions-row.svelte-6qi2q9 {display:flex;gap:12px;flex-wrap:wrap;margin-top:8px;}"
};
function va(e, t) {
	qe(t, !1), Bi(e, _a);
	let n = na(t, "apiBase", 12, ""), r = /* @__PURE__ */ k(""), i = /* @__PURE__ */ k(""), a = /* @__PURE__ */ k(""), o = /* @__PURE__ */ k(!1), s = /* @__PURE__ */ k(!1), c = /* @__PURE__ */ k(!0), l = /* @__PURE__ */ k(!1), u = /* @__PURE__ */ k(!1), d = /* @__PURE__ */ k(!1), f = /* @__PURE__ */ k(!1), p = /* @__PURE__ */ k(!1), m = /* @__PURE__ */ k(!1);
	Li(async () => {
		await g(), A(c, !1);
	});
	async function h() {
		try {
			A(m, !0), await fetch(`${n()}/activate`, { method: "POST" }), await g();
		} catch (e) {
			console.error("Failed to activate server:", e);
		} finally {
			A(m, !1);
		}
	}
	async function g() {
		try {
			let e = await (await fetch(`${n()}/settings`)).json();
			e?.settings && (A(r, e.settings.base_url || ""), A(i, e.settings.username || ""), A(o, e.settings.has_password || !1), A(s, e.settings.connected || !1), A(p, e.settings.is_active || !1), A(a, ""));
		} catch (e) {
			console.error("Failed to load Navidrome settings:", e);
		}
	}
	async function ee() {
		if (!Z(r).trim()) console.error("Server URL is required");
		else if (!Z(i).trim() || !Z(o) && !Z(a).trim()) console.error("Username and password are required");
		else try {
			A(l, !0), await fetch(`${n()}/settings`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					base_url: Z(r),
					username: Z(i),
					password: Z(a)
				})
			}), await g();
		} catch (e) {
			console.error("Failed to save Navidrome settings:", e);
		} finally {
			A(l, !1);
		}
	}
	async function te() {
		try {
			A(u, !0), (await (await fetch(`${n()}/test-connection`, { method: "POST" })).json())?.connected && await g();
		} catch (e) {
			console.error("Connection test failed:", e);
		} finally {
			A(u, !1);
		}
	}
	var ne = {
		get apiBase() {
			return n();
		},
		set apiBase(e) {
			n(e), Kt();
		}
	};
	Qi();
	var _ = ga(), v = Q(_), re = Q(v), ie = $(Q(re), 2), ae = Q(ie), oe = (e) => {
		wi(e, la());
	};
	zi(ae, (e) => {
		Z(p) && e(oe);
	});
	var y = $(ae, 2), b = (e) => {
		wi(e, ua());
	};
	zi(y, (e) => {
		Z(o) && e(b);
	});
	var se = $(y, 2), ce = (e) => {
		wi(e, da());
	}, le = (e) => {
		wi(e, fa());
	};
	zi(se, (e) => {
		Z(s) ? e(ce) : Z(o) && e(le, 1);
	}), w(ie), w(re);
	var x = $(re, 2), ue = Nr(x, !0);
	w(v);
	var S = $(v, 2), C = (e) => {
		wi(e, pa());
	}, de = (e) => {
		var t = ha(), n = $(Q(t), 2), s = Q(n), c = $(Q(s), 2);
		Wi(c), fe(2), w(s);
		var d = $(s, 2), g = $(Q(d), 2);
		Wi(g), w(d);
		var ne = $(d, 2), _ = $(Q(ne), 2), v = Q(_);
		Wi(v);
		var re = $(v, 2), ie = Nr(re, !0);
		w(_), w(ne);
		var ae = $(ne, 2), oe = Q(ae), y = Nr(oe, !0), b = $(oe, 2), se = (e) => {
			var t = ma(), n = Nr(t, !0);
			hn(() => {
				t.disabled = Z(u), ki(n, Z(u) ? "Testing..." : "Test Connection");
			}), pi("click", t, te), wi(e, t);
		};
		zi(b, (e) => {
			Z(o) && e(se);
		});
		var ce = $(b, 2), le = (e) => {
			var t = ma(), n = Nr(t, !0);
			hn(() => {
				t.disabled = Z(m), ki(n, Z(m) ? "Activating..." : "Activate Server");
			}), pi("click", t, h), wi(e, t);
		};
		zi(ce, (e) => {
			Z(p) || e(le);
		}), w(ae), w(n), w(t), hn(() => {
			Gi(v, "type", Z(f) ? "text" : "password"), Gi(v, "placeholder", Z(o) ? "••••••••" : "Enter password"), ki(ie, Z(f) ? "🙈" : "👁️"), oe.disabled = Z(l), ki(y, Z(l) ? "Saving..." : "Save Settings");
		}), Yi(c, () => Z(r), (e) => A(r, e)), Yi(g, () => Z(i), (e) => A(i, e)), Yi(v, () => Z(a), (e) => A(a, e)), pi("click", re, () => A(f, !Z(f))), pi("click", oe, ee), wi(e, t);
	};
	return zi(S, (e) => {
		Z(c) ? e(C) : Z(d) || e(de, 1);
	}), w(_), hn(() => ki(ue, Z(d) ? "Expand" : "Collapse")), pi("click", x, () => A(d, !Z(d))), wi(e, _), Je(ne);
}
customElements.define("navidrome-dashboard-card", ca(va, { apiBase: {} }, [], [], { mode: "open" }));
export { va as default };
